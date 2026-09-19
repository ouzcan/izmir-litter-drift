"""İzmir Körfezi yerel hidrodinamik modeli — Delft3D FM (D-Flow FM) kurucu.

dfm_tools "modelbuilder" zincirinin İzmir'e uyarlanmış hâli:
  mesh    : meshkernel ile esnek ağ (batimetriye göre 500 → ~120 m), kara kesimi, açık sınır polyline'ı, *_net.nc
  forcing : CMEMS (zos, so, thetao, uo, vo) sınır koşulları + ERA5 meteo (+ 3D için CMEMS başlangıç alanı, gelgit isteğe bağlı)
  mdu     : model tanım dosyası, gözlem noktaları, DIMR + run.bat

Kullanım (kullanıcının bilgisayarında, conda 'litter' ortamı, depo kökünden):
    python scripts/30_build_dflowfm.py --stage mesh
    python scripts/30_build_dflowfm.py --stage forcing --start 2026-09-06 --end 2026-09-13 --model 2D
    python scripts/30_build_dflowfm.py --stage mdu     --start 2026-09-06 --end 2026-09-13 --model 2D
    python scripts/30_build_dflowfm.py --stage all ...
Çıktı: runs/dflowfm/<ad>_<2D|3D>/ (ağ, .pli, .bc, .ext, .mdu, dimr_config.xml, run_parallel.bat)
"""
from __future__ import annotations
import argparse, glob, os, shutil, sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from common import ROOT, RAW, PROC, RUNS, CFG, bbox, params, load_env

load_env()
P = params()
D = P.get("dflowfm", {})
CRS = "EPSG:4326"

# ----------------------------------------------------------------------------- yardımcılar
def log(*a):
    print("[30]", *a, flush=True)

def load_bathy(lon0, lon1, lat0, lat1) -> xr.DataArray:
    """EMODnet (tercih) veya GEBCO yerel dosyası; koordinatlar lon/lat olarak döner, deniz negatif."""
    cands = [RAW / "bathy" / "emodnet_dtm2024_A.nc", RAW / "bathy" / "gebco_A.nc"]
    for f in cands:
        if f.exists():
            ds = xr.open_dataset(f)
            var = "elevation" if "elevation" in ds else list(ds.data_vars)[0]
            da = ds[var]
            ren = {}
            for k in da.dims:
                if k.lower().startswith("lat"): ren[k] = "lat"
                if k.lower().startswith("lon"): ren[k] = "lon"
            da = da.rename(ren)
            if da.lat[0] > da.lat[-1]:
                da = da.sortby("lat")
            da = da.sel(lon=slice(lon0 - 0.1, lon1 + 0.1), lat=slice(lat0 - 0.1, lat1 + 0.1)).load()
            log(f"batimetri: {f.name}, {dict(da.sizes)}")
            return da.astype("float64")
    sys.exit("Batimetri yok: önce `python scripts/20_fetch_bathymetry.py` çalıştır.")

def load_land_gdf(lon0, lon1, lat0, lat1):
    """OSM kara poligonları varsa onlar, yoksa GSHHS 'f' (dfm_tools indirir)."""
    import geopandas as gpd
    import dfm_tools as dfmt
    f = PROC / "osm_land_izmir.gpkg"
    if f.exists():
        gdf = gpd.read_file(f, bbox=(lon0, lat0, lon1, lat1))
        log(f"kara: OSM poligonları ({len(gdf)})")
        return gdf, "osm"
    gs = dfmt.get_coastlines_gdb(res="f", bbox=(lon0, lat0, lon1, lat1), crs=CRS)
    gdf = gpd.GeoDataFrame(geometry=gs.geometry, crs=CRS) if not hasattr(gs, "geometry") else gs
    log(f"kara: GSHHS f ({len(gdf)})")
    return gdf, "gshhs"

def bndpli_cut_with_gdf(mk, land_gdf, buffer_deg):
    """Ağ dış çevresinden açık sınır polyline'ı üret; kara (tamponlu) içinde kalan kısımları at."""
    import geopandas as gpd
    from shapely.geometry import LineString, MultiLineString, MultiPolygon
    from shapely.ops import linemerge, unary_union
    from dfm_tools.meshkernel_helpers import meshkernel_get_outer_xycoords
    x, y = meshkernel_get_outer_xycoords(mk)
    ring = LineString(np.c_[x, y])
    land = unary_union([g for g in land_gdf.geometry if g is not None]).buffer(buffer_deg)
    bnd = ring.difference(land)
    if isinstance(bnd, MultiLineString):
        bnd = linemerge(bnd)
    geoms = list(bnd.geoms) if isinstance(bnd, MultiLineString) else [bnd]
    # çok kısa parçaları at (< 3 km)
    geoms = [g for g in geoms if g.length > 0.03]
    # yalnız izin verilen kutu kenarlarındaki parçalar açık sınır olur (güvenlik: doğu/güney kara olmalı)
    allowed = set(D.get("open_edges", ["north", "west"]))
    x0, x1, y0, y1 = x.min(), x.max(), y.min(), y.max()
    tol = 0.002
    def edge_of(g):
        xs, ys = np.array(g.coords)[:, 0], np.array(g.coords)[:, 1]
        e = set()
        if np.mean(np.abs(ys - y1) < tol) > 0.5: e.add("north")
        if np.mean(np.abs(ys - y0) < tol) > 0.5: e.add("south")
        if np.mean(np.abs(xs - x0) < tol) > 0.5: e.add("west")
        if np.mean(np.abs(xs - x1) < tol) > 0.5: e.add("east")
        # köşe dönen parçalar: her nokta bir kenara yakın mı?
        near = (np.abs(ys - y1) < tol) | (np.abs(ys - y0) < tol) | (np.abs(xs - x0) < tol) | (np.abs(xs - x1) < tol)
        if near.mean() > 0.9:
            if (np.abs(ys - y1) < tol).any(): e.add("north")
            if (np.abs(ys - y0) < tol).any(): e.add("south")
            if (np.abs(xs - x0) < tol).any(): e.add("west")
            if (np.abs(xs - x1) < tol).any(): e.add("east")
        return e
    kept = []
    for g in geoms:
        e = edge_of(g)
        if e and e.issubset(allowed):
            kept.append(g)
        else:
            log(f"uyarı: {sorted(e) or 'kenar dışı'} üzerindeki {g.length*111:.0f} km'lik sınır parçası atıldı (open_edges={sorted(allowed)})")
    return gpd.GeoDataFrame(geometry=kept, crs=CRS)

# ----------------------------------------------------------------------------- aşama: mesh
def stage_mesh(out: Path, name: str):
    import dfm_tools as dfmt
    import meshkernel
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

    lon0, lon1, lat0, lat1 = bbox(D.get("domain_id", "B_model"))
    dxy = float(D.get("base_dxy_deg", 0.005))
    min_edge = float(D.get("min_edge_m", 120))
    courant_t = float(D.get("max_courant_time_s", 20))
    log(f"alan {lon0}-{lon1}E {lat0}-{lat1}N, taban {dxy}°, min kenar {min_edge} m, Courant {courant_t} s")

    mk = dfmt.make_basegrid(lon_min=lon0, lon_max=lon1, lat_min=lat0, lat_max=lat1, dx=dxy, dy=dxy, crs=CRS)
    lon0, lat0, lon1, lat1 = dfmt.meshkernel_get_bbox(mk)

    bathy = load_bathy(lon0, lon1, lat0, lat1)
    land_gdf, land_src = load_land_gdf(lon0, lon1, lat0, lat1)

    # açık sınır: kara kesilmeden ÖNCE, taban/inceltilmiş ağ üzerinden
    dfmt.refine_basegrid(mk=mk, data_bathy_sel=bathy, min_edge_size=min_edge, max_courant_time=courant_t)
    bnd_gdf = bndpli_cut_with_gdf(mk, land_gdf, buffer_deg=float(D.get("bnd_land_buffer_deg", 0.01)))
    bnd_gdf = dfmt.interpolate_bndpli(bnd_gdf, res=float(D.get("bnd_point_spacing_deg", 0.02)))
    pli = dfmt.geodataframe_to_PolyFile(bnd_gdf, name=f"{name}_bnd")
    pli_file = out / f"{name}.pli"; pli.save(pli_file)
    log(f"açık sınır: {len(bnd_gdf)} parça -> {pli_file.name}")

    # kara kesimi
    dfmt.meshkernel_delete_withgdf(mk=mk, coastlines_gdf=land_gdf)
    illegal = dfmt.meshkernel_get_illegalcells(mk=mk)
    if len(illegal) > 0:
        ipoly = dfmt.geodataframe_to_PolyFile(illegal); ipoly.save(out / "illegalcells.pol")
        log(f"uyarı: {len(illegal)} kötü hücre -> illegalcells.pol (drypoints)")

    # batimetri interpolasyonu + net.nc
    uds = dfmt.meshkernel_to_UgridDataset(mk=mk, crs=CRS)
    zi = bathy.interp(lon=uds.obj.mesh2d_node_x, lat=uds.obj.mesh2d_node_y).drop_vars(["lon", "lat"])
    zi = zi.interpolate_na(dim="mesh2d_nNodes") if "mesh2d_nNodes" in zi.dims else zi
    uds["mesh2d_node_z"] = zi.clip(max=float(D.get("bedlevel_clip_max_m", 5)))
    uds.obj.mesh2d_node_z.encoding["_FillValue"] = 1e20
    netfile = out / f"{name}_net.nc"; uds.ugrid.to_netcdf(netfile)
    m2d = mk.mesh2d_get()
    nn, nf = len(m2d.node_x), int(len(m2d.face_nodes) / max(1, m2d.nodes_per_face.max())) if hasattr(m2d, "nodes_per_face") else -1
    log(f"ağ: {len(m2d.node_x)} düğüm, {len(m2d.edge_nodes)//2} kenar -> {netfile.name}")

    # görsel
    fig, ax = plt.subplots(figsize=(10, 8))
    uds.mesh2d_node_z.ugrid.plot(ax=ax, vmin=-80, vmax=0, cmap="Blues_r", add_colorbar=True)
    uds.grid.plot(ax=ax, linewidth=0.15, color="k", alpha=0.35)
    bnd_gdf.plot(ax=ax, color="r", linewidth=2)
    ax.set_aspect(1 / np.cos(np.deg2rad(38.6))); ax.set_title(f"{name}: ağ + batimetri + açık sınır (kırmızı) — kara: {land_src}")
    fig.savefig(out / "mesh.png", dpi=130, bbox_inches="tight")
    ax.set_xlim(27.0, 27.2); ax.set_ylim(38.38, 38.50); ax.set_title("iç körfez yakın plan")
    fig.savefig(out / "mesh_ic_korfez.png", dpi=130, bbox_inches="tight")
    log("görseller: mesh.png, mesh_ic_korfez.png")
    return netfile, pli_file, illegal

# ----------------------------------------------------------------------------- aşama: forcing
def stage_forcing(out: Path, name: str, start: str, end: str, model: str, tide: bool):
    import dfm_tools as dfmt
    import hydrolib.core.dflowfm as hcdfm
    pli_file = out / f"{name}.pli"
    if not pli_file.exists():
        sys.exit("Önce --stage mesh")
    lon0, lon1, lat0, lat1 = bbox(D.get("domain_id", "B_model"))
    ext_new = hcdfm.ExtModel(); ext_old = hcdfm.ExtOldModel()
    ref_date = D.get("ref_date", "2025-01-01")

    ext_new = dfmt.constant_to_bc(ext_new=ext_new, file_pli=str(pli_file), constant=0.0)
    if tide:
        log("gelgit: tpxo80_opendap")
        dfmt.interpolate_tide_to_bc(ext_new=ext_new, tidemodel="tpxo80_opendap", file_pli=str(pli_file), component_list=None)

    skip_dl = os.environ.get("LITTER_SKIP_DOWNLOAD") == "1"   # yeniden dönüştürme için indirmeyi atla
    # CMEMS — MED (1/24°) ürünleri açıkça verilir; dfm_tools varsayılanı GLOBAL (1/12°) olurdu
    dcm = out / "data" / "cmems"; dcm.mkdir(parents=True, exist_ok=True)
    cm_ids = D.get("cmems_datasets", {})
    for vk in ([] if skip_dl else ["zos", "so", "thetao", "uo", "vo"]):
        dfmt.download_CMEMS(varkey=vk, dataset_id=cm_ids.get(vk),
                            longitude_min=lon0 - 0.2, longitude_max=lon1 + 0.2,
                            latitude_min=lat0 - 0.2, latitude_max=lat1 + 0.2,
                            date_min=start, date_max=end, dir_output=str(dcm), file_prefix="cmems_", overwrite=False)
    pattern = str(dcm / "cmems_{ncvarname}_*.nc")
    ext_new = dfmt.cmems_nc_to_bc(ext_new=ext_new, refdate_str=f"minutes since {ref_date} 00:00:00 +00:00",
                                  dir_output=str(out),
                                  list_quantities=["waterlevelbnd", "salinitybnd", "temperaturebnd", "uxuyadvectionvelocitybnd"],
                                  tstart=start, tstop=end, file_pli=str(pli_file), dir_pattern=pattern)
    if model == "3D":
        ext_old = dfmt.cmems_nc_to_ini(ext_old=ext_old, dir_output=str(out),
                                       list_quantities=["salinitybnd", "temperaturebnd"], tstart=start, dir_pattern=pattern)

    # ERA5
    dera = out / "data" / "era5"; dera.mkdir(parents=True, exist_ok=True)
    vks = ["msl", "u10n", "v10n", "chnk"]
    if model == "3D":
        vks += ["d2m", "t2m", "tcc", "ssr", "strd", "mer", "mtpr"]
    for vk in ([] if skip_dl else vks):
        dfmt.download_ERA5(vk, longitude_min=lon0 - 0.5, longitude_max=lon1 + 0.5, latitude_min=lat0 - 0.5, latitude_max=lat1 + 0.5,
                           date_min=start, date_max=end, dir_output=str(dera), overwrite=False)
    ext_old = dfmt.preprocess_merge_meteofiles_era5(ext_old=ext_old, varkey_list=vks, dir_data=str(dera),
                                                    dir_output=str(out), time_slice=slice(start, end))
    ext_new.save(filepath=str(out / f"{name}_new.ext"))
    ext_old.save(filepath=str(out / f"{name}_old.ext"))
    log("zorlama dosyaları yazıldı:", f"{name}_new.ext", f"{name}_old.ext")

# ----------------------------------------------------------------------------- aşama: mdu
def stage_mdu(out: Path, name: str, start: str, end: str, model: str, nproc: int):
    import dfm_tools as dfmt
    import hydrolib.core.dflowfm as hcdfm
    netfile = out / f"{name}_net.nc"
    if not netfile.exists():
        sys.exit("Önce --stage mesh (ve forcing)")
    ref_date = D.get("ref_date", "2025-01-01")

    # gözlem noktaları
    obs = pd.read_csv(CFG / "obs_points.csv")
    obs_file = out / f"{name}_obs.xyn"
    obs[["lon", "lat", "name"]].to_csv(obs_file, sep=" ", header=False, index=False, quoting=2)

    mdu = hcdfm.FMModel()
    mdu.geometry.netfile = str(netfile)
    mdu.geometry.openboundarytolerance = 0.1
    mdu.geometry.bedlevuni = 5
    mdu.geometry.dxwuimin2d = 0.1
    if (out / "illegalcells.pol").exists():
        mdu.geometry.drypointsfile = [hcdfm.PolyFile(out / "illegalcells.pol")]
    mdu.numerics.izbndpos = 1
    mdu.numerics.mintimestepbreak = 0.1
    mdu.numerics.keepstbndonoutflow = 1
    mdu.numerics.barocponbnd = 1
    mdu.numerics.vertadvtypsal = 4
    mdu.numerics.vertadvtyptem = 4
    mdu.physics.rhomean = 1028.0            # Ege
    mdu.wind.icdtyp = 4                     # ERA5 Charnock
    mdu.wind.cdbreakpoints = [0.025]
    mdu.wind.pavbnd = 101330
    mdu.time.refdate = pd.Timestamp(ref_date).strftime("%Y%m%d")
    mdu.time.tunit = "S"
    mdu.time.dtmax = float(D.get("dtmax_s", 30))
    mdu.time.startdatetime = pd.Timestamp(start).strftime("%Y%m%d%H%M%S")
    mdu.time.stopdatetime = pd.Timestamp(end).strftime("%Y%m%d%H%M%S")
    ext_old_f = out / f"{name}_old.ext"; ext_new_f = out / f"{name}_new.ext"
    if ext_old_f.exists():
        mdu.external_forcing.extforcefile = str(ext_old_f)
    if ext_new_f.exists():
        mdu.external_forcing.extforcefilenew = hcdfm.ExtModel(ext_new_f)   # bc yolları çözülemezse burada hata verir
    mdu.output.obsfile = [str(obs_file)]
    mdu.output.hisinterval = [600]
    mdu.output.mapinterval = [float(D.get("map_interval_s", 3600))]
    mdu.output.rstinterval = [0]
    mdu.output.statsinterval = [3600]
    if model == "3D":
        mdu.geometry.layertype = 1
        mdu.geometry.kmx = int(D.get("kmx", 10))
        mdu.physics.iniwithnudge = 2
        mdu.physics.salinity = 1
        mdu.physics.temperature = 5
        mdu.physics.initialsalinity = 38.8
        mdu.physics.heat_eachstep = 1
        try:
            mdu.wind.rhowaterinwindstress = 1
        except Exception:  # eski hydrolib sürümü
            pass
    mdu_file = out / f"{name}.mdu"
    mdu.save(str(mdu_file))
    dfmt.make_paths_relative(str(mdu_file))

    dimrset = os.environ.get("DIMRSET_FOLDER") or next(iter(sorted(glob.glob(
        r"C:\Program Files\Deltares\Delft3D FM Suite*\plugins\DeltaShell.Dimr\kernels"))), None)
    dfmt.create_model_exec_files(file_mdu=str(mdu_file), nproc=nproc, dimrset_folder=dimrset)
    log(f"mdu: {mdu_file.name}; dimrset: {dimrset or 'bulunamadı (run_parallel.bat elle düzenlenir)'}")

# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["mesh", "forcing", "mdu", "all"], default="mesh")
    ap.add_argument("--model", choices=["2D", "3D"], default="2D")
    ap.add_argument("--start", default="2026-09-06"); ap.add_argument("--end", default="2026-09-13")
    ap.add_argument("--name", default=D.get("model_name", "izmir"))
    ap.add_argument("--tide", action="store_true", help="TPXO8 gelgit ekle (opendap erişimi gerekir)")
    ap.add_argument("--nproc", type=int, default=int(D.get("nproc", 4)))
    a = ap.parse_args()
    out = (RUNS / "dflowfm" / f"{a.name}_{a.model}").resolve(); out.mkdir(parents=True, exist_ok=True)
    log("çıktı klasörü:", out)
    if a.stage in ("mesh", "all"):
        stage_mesh(out, a.name)
    if a.stage in ("forcing", "all"):
        stage_forcing(out, a.name, a.start, a.end, a.model, a.tide)
    if a.stage in ("mdu", "all"):
        stage_mdu(out, a.name, a.start, a.end, a.model, a.nproc)

if __name__ == "__main__":
    main()
