"""SCHISM scribe çıktısını (out2d_N.nc + horizontalVelX/Y_N.nc) OpenDrift'in yerel SCHISM okuyucusunun
(`reader_schism_native`) anladığı tek bir "schout benzeri" dosyaya çevir.

Neden dönüştürme: OpenDrift 1.14'ün okuyucusu eski SCHISM biçimini bekler (`elev`, `dahv[time,node,2]`,
`hvel`, `zcor`, `SCHISM_hgrid_face_nodes` üçgen). Ayrıca okuyucu enlem-boylam ağda 3B hızı KULLANAMAZ
(kod use_3d=False'a düşer). Yüzen çöp için gereken yüzey akıntısı olduğundan, 3B koşunun EN ÜST sigma
katmanındaki hız burada `dahv` adıyla yazılır (okuyucu 2B modda `dahv`'ı okur). 2B koşuda derinlik-ort. hız yazılır.

Kullanım:
    python scripts/40_schism_to_opendrift.py --run izmir3d            # → runs/schism/izmir3d/opendrift/schism_surface.nc
    python scripts/40_schism_to_opendrift.py --run izmir --layer dav  # 2B koşu: derinlik-ort. hız
Seçenekler: --layer top|dav|<k> (k: sigma seviyesi indeksi, 1=dip … nvrt=yüzey); --stride N (her N. kayıt)
"""
from __future__ import annotations
import argparse, glob
from pathlib import Path
import numpy as np
import xarray as xr

from common import RUNS, params

S = params().get("schism", {})

def log(*a): print("[40]", *a, flush=True)

def stacks(run: Path, var: str):
    fs = glob.glob(str(run / "outputs" / f"{var}_*.nc"))
    return sorted(fs, key=lambda f: int(Path(f).stem.split("_")[-1]))

def tri_faces(fn: np.ndarray) -> np.ndarray:
    """SCHISM yüz tablosu (1 tabanlı, dörtgenlerde 4. sütun NaN/-1) → üçgenler (1 tabanlı)."""
    fn = np.array(fn, dtype=float)
    q = np.isfinite(fn[:, 3]) & (fn[:, 3] > 0) if fn.shape[1] > 3 else np.zeros(len(fn), bool)
    t1 = fn[:, :3]
    t2 = fn[q][:, [0, 2, 3]]
    return np.vstack([t1, t2]).astype("i4")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=S.get("run_name", "izmir"))
    ap.add_argument("--layer", default="top", help="top (3B en üst sigma), dav (derinlik-ort.), ya da seviye no")
    ap.add_argument("--stride", type=int, default=1)
    ap.add_argument("--out", default=None)
    ap.add_argument("--t0", default=None, help="bu zamandan önceki kayıtları at (ısınma payı), örn. 2025-09-01")
    ap.add_argument("--t1", default=None, help="bu zamandan sonraki kayıtları at (dahil değil)")
    ap.add_argument("--epoch", default="2025-01-01", help="time birimi: 'seconds since <epoch>' — aylık dosyalar aynı epoch ile birleşir")
    a = ap.parse_args()
    run = RUNS / "schism" / a.run
    f2 = stacks(run, "out2d")
    if not f2: raise SystemExit(f"out2d_*.nc yok: {run/'outputs'}")
    fx, fy = stacks(run, "horizontalVelX"), stacks(run, "horizontalVelY")
    use3d = a.layer != "dav" and bool(fx)
    if a.layer != "dav" and not fx:
        log("uyarı: horizontalVelX yok (2B koşu) → derinlik-ort. hız kullanılıyor"); a.layer = "dav"

    o = xr.open_mfdataset(f2, combine="nested", concat_dim="time", data_vars="minimal", coords="minimal", compat="override")
    x = o.SCHISM_hgrid_node_x.values; y = o.SCHISM_hgrid_node_y.values; dep = o.depth.values.astype("f4")
    faces = tri_faces(o.SCHISM_hgrid_face_nodes.values)
    tall = o.time.values
    sel = np.ones(len(tall), bool)
    if a.t0: sel &= tall >= np.datetime64(a.t0)
    if a.t1: sel &= tall < np.datetime64(a.t1)
    idx = np.where(sel)[0][::a.stride]
    if len(idx) == 0: raise SystemExit("seçilen zaman aralığında kayıt yok")
    t = tall[idx]
    elev = o.elevation.isel(time=idx).values.astype("f4")
    dry = o.dryFlagNode.isel(time=idx).values.astype("i1")
    if use3d:
        hx = xr.open_mfdataset(fx, combine="nested", concat_dim="time", data_vars="minimal", coords="minimal", compat="override")
        hy = xr.open_mfdataset(fy, combine="nested", concat_dim="time", data_vars="minimal", coords="minimal", compat="override")
        nv = hx.sizes["nSCHISM_vgrid_layers"]
        k = nv - 1 if a.layer == "top" else int(a.layer) - 1
        u = hx.horizontalVelX.isel(nSCHISM_vgrid_layers=k, time=idx).values.astype("f4")
        v = hy.horizontalVelY.isel(nSCHISM_vgrid_layers=k, time=idx).values.astype("f4")
        src = f"horizontalVel sigma seviyesi {k+1}/{nv} ({'yüzey' if k == nv-1 else 'ara'})"
    else:
        u = o.depthAverageVelX.isel(time=idx).values.astype("f4")
        v = o.depthAverageVelY.isel(time=idx).values.astype("f4")
        src = "depthAverageVel (2B)"
    u = np.nan_to_num(u); v = np.nan_to_num(v); elev = np.nan_to_num(elev)
    u[dry == 1] = 0; v[dry == 1] = 0

    base = a.epoch + " 00:00:00"
    secs = ((t - np.datetime64(a.epoch)) / np.timedelta64(1, "s")).astype("f8")
    ds = xr.Dataset(
        {
            "SCHISM_hgrid_node_x": (("nSCHISM_hgrid_node",), x, {"standard_name": "longitude", "units": "degrees_east", "long_name": "node x-coordinate"}),
            "SCHISM_hgrid_node_y": (("nSCHISM_hgrid_node",), y, {"standard_name": "latitude", "units": "degrees_north", "long_name": "node y-coordinate"}),
            "SCHISM_hgrid_face_nodes": (("nSCHISM_hgrid_face", "nMaxSCHISM_hgrid_face_nodes"), faces, {"long_name": "element connectivity (triangles, 1-based)", "start_index": 1}),
            "depth": (("nSCHISM_hgrid_node",), dep, {"long_name": "bathymetry", "units": "m", "positive": "down"}),
            "elev": (("time", "nSCHISM_hgrid_node"), elev, {"long_name": "water surface elevation", "units": "m"}),
            "dahv": (("time", "nSCHISM_hgrid_node", "two"), np.stack([u, v], axis=-1), {"long_name": f"horizontal velocity used by OpenDrift as 2D field: {src}", "units": "m/s"}),
            "wetdry_node": (("time", "nSCHISM_hgrid_node"), dry, {"long_name": "1=dry"}),
        },
        coords={"time": ("time", secs, {"standard_name": "time", "long_name": "time", "units": f"seconds since {base}", "base_date": base})},
        attrs={"title": "SCHISM surface fields for OpenDrift reader_schism_native", "source_run": str(run), "velocity_source": src,
               "Conventions": "CF-1.0", "note": "quads split into triangles; dahv holds the chosen layer velocity"},
    )
    out = Path(a.out) if a.out else run / "opendrift" / f"schism_{'surface' if use3d else 'dav'}.nc"
    out.parent.mkdir(exist_ok=True)
    enc = {k: {"zlib": True, "complevel": 3} for k in ("elev", "dahv")}
    ds.to_netcdf(out, format="NETCDF4", encoding=enc)
    sp = np.hypot(u, v)
    log(f"{len(t)} kayıt ({str(t[0])[:16]} → {str(t[-1])[:16]}, adım {(secs[1]-secs[0]) if len(secs) > 1 else 0:.0f} s), {len(x)} düğüm, {len(faces)} üçgen; hız kaynağı: {src}")
    log(f"|u| medyan {np.median(sp[-1]):.3f} maks {sp.max():.3f} m/s; dosya {out} ({out.stat().st_size/1e6:.0f} MB)")

if __name__ == "__main__":
    main()
