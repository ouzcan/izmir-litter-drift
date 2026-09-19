"""CMEMS + ERA5 → SCHISM zorlama dosyaları.

Alt komutlar (depo kökünden, conda 'litter' ortamı; indirme kullanıcının bilgisayarında):
  download  : Copernicus MED (zos saatlik 2D; so/thetao/uo/vo günlük 3D) + ERA5 (u10 v10 msl t2m d2m)
              → data/raw/forcing/
  boundary  : açık sınır düğümlerinde zaman serileri → runs/schism/<ad>/elev2D.th.nc (+3D: uv3D, TEM_3D, SAL_3D .th.nc,
              temp.ic, salt.ic)
  sflux     : ERA5 → runs/schism/<ad>/sflux/sflux_air_1.NNNN.nc (günlük dosyalar) + sflux_inputs.txt
  all       : boundary + sflux

Örnek:
  python scripts/32_forcing_to_schism.py download --start 2026-09-06 --end 2026-09-13
  python scripts/32_forcing_to_schism.py all --start 2026-09-06 --end 2026-09-13 --mode 2d
Zaman ekseni: SCHISM .th.nc dosyalarında kayıt k → t = k*time_step (t=0 = --start 00:00 UTC).
"""
from __future__ import annotations
import argparse, glob, os
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import xarray as xr

from common import ROOT, RAW, RUNS, bbox, params, load_env

load_env()
P = params(); S = P.get("schism", {}); CM = P.get("dflowfm", {}).get("cmems_datasets", {})
FDIR = RAW / "forcing"
COSLAT = np.cos(np.deg2rad(38.6))

def log(*a): print("[32]", *a, flush=True)

# ============================================================================ download
def cmd_download(a):
    import copernicusmarine as cm
    FDIR.mkdir(parents=True, exist_ok=True)
    lon0, lon1, lat0, lat1 = bbox("B_model")
    t0 = datetime.fromisoformat(a.start) - timedelta(days=1); t1 = datetime.fromisoformat(a.end) + timedelta(days=1)
    tag = f"{a.start}_{a.end}"
    for var, ds_id in [("zos", CM["zos"]), ("so", CM["so"]), ("thetao", CM["thetao"]), ("uo", CM["uo"]), ("vo", CM["vo"])]:
        out = FDIR / f"cmems_{var}_{tag}.nc"
        if out.exists(): log("atla", out.name); continue
        log(f"CMEMS {var} <- {ds_id}")
        cm.subset(dataset_id=ds_id, variables=[var],
                  minimum_longitude=lon0 - 0.25, maximum_longitude=lon1 + 0.25,
                  minimum_latitude=lat0 - 0.25, maximum_latitude=lat1 + 0.25,
                  start_datetime=t0.isoformat(), end_datetime=t1.isoformat(),
                  output_filename=out.name, output_directory=str(FDIR))
    # ERA5
    import cdsapi
    A = bbox("A_il_kiyisi")
    out = FDIR / f"era5_{tag}.nc"
    if out.exists(): log("atla", out.name)
    else:
        days = [t0 + timedelta(days=i) for i in range((t1 - t0).days + 1)]
        req = {"product_type": ["reanalysis"],
               "variable": ["10m_u_component_of_wind", "10m_v_component_of_wind", "mean_sea_level_pressure",
                            "2m_temperature", "2m_dewpoint_temperature"],
               "year": sorted({f"{d.year}" for d in days}), "month": sorted({f"{d.month:02d}" for d in days}),
               "day": sorted({f"{d.day:02d}" for d in days}), "time": [f"{h:02d}:00" for h in range(24)],
               "area": [A[3], A[0], A[2], A[1]], "data_format": "netcdf", "download_format": "unarchived"}
        log("ERA5 istek (kuyruk birkaç dk sürebilir)")
        cdsapi.Client().retrieve("reanalysis-era5-single-levels", req, str(out))
    log("indirme tamam:", FDIR)

# ============================================================================ yardımcılar
def newest(pattern):
    fs = sorted(glob.glob(str(FDIR / pattern)), key=os.path.getmtime)
    if not fs: raise SystemExit(f"{FDIR}/{pattern} yok — önce `download`")
    return fs[-1]

def read_hgrid(p: Path):
    lines = p.read_text().splitlines()
    ne, nn = map(int, lines[1].split())
    xyz = np.array([[float(v) for v in l.split()[1:4]] for l in lines[2:2 + nn]])
    i = 2 + nn + ne; nope = int(lines[i].split()[0]); j = i + 2; opens = []
    for _ in range(nope):
        n = int(lines[j].split()[0]); opens.append([int(v) - 1 for v in lines[j + 1:j + 1 + n]]); j += 1 + n
    return xyz, opens

def read_vgrid(p: Path):
    """SZ vgrid (ivcor=2, kz=1) → sigma dizisi ve (h_c, theta_b, theta_f)."""
    lines = [l.split("!")[0].strip() for l in p.read_text().splitlines()]
    assert lines[0].startswith("2"), "yalnız ivcor=2 (SZ) destekleniyor"
    nvrt, kz, hs = int(lines[1].split()[0]), int(lines[1].split()[1]), float(lines[1].split()[2])
    k = 2 + 1 + kz  # 'Z levels' + kz satır
    assert lines[k].lower().startswith("s levels")
    hc, tb, tf = map(float, lines[k + 1].split()[:3])
    sig = np.array([float(lines[k + 2 + i].split()[1]) for i in range(nvrt - kz + 1)])
    return nvrt, sig, hc, tb, tf

def z_levels(h, sig, hc, tb, tf):
    """SCHISM S-koordinat dönüşümü (eta=0): düğüm derinliği h (pozitif) → z (negatif aşağı), her sigma için."""
    cs = (1 - tb) * np.sinh(tf * sig) / np.sinh(tf) + tb * (np.tanh(tf * (sig + 0.5)) / (2 * np.tanh(0.5 * tf)) - 0.5)
    h = np.atleast_1d(h)[:, None]
    z = np.where(h > hc, hc * sig[None, :] + (h - hc) * cs[None, :], h * sig[None, :])
    return z  # (n, nvrt)

def open_cm(var):
    ds = xr.open_dataset(newest(f"cmems_{var}_*.nc"))
    da = ds[var]
    ren = {}
    for d in da.dims:
        if d.lower().startswith("lat"): ren[d] = "lat"
        if d.lower().startswith("lon"): ren[d] = "lon"
    da = da.rename(ren)
    if da.lat[0] > da.lat[-1]: da = da.sortby("lat")
    return da.load()

def nearest_valid_index(da, px, py):
    """Her nokta için CMEMS gridinde (yüzeyde) geçerli en yakın hücrenin (iy, ix) indeksleri."""
    from scipy.spatial import cKDTree
    surf = da.isel(time=0)
    if "depth" in surf.dims: surf = surf.isel(depth=0)
    valid = np.isfinite(surf.values)
    LON, LAT = np.meshgrid(da.lon.values, da.lat.values)
    iy, ix = np.where(valid)
    tree = cKDTree(np.c_[LON[valid] * COSLAT, LAT[valid]])
    d, k = tree.query(np.c_[px * COSLAT, py])
    if (d * 111000).max() > 15000:
        log(f"uyarı: bazı düğümler en yakın geçerli CMEMS hücresine {d.max()*111000/1000:.0f} km uzakta")
    return iy[k], ix[k]

def to_regular_time(da, t_axis):
    """CMEMS zaman eksenini (datetime64) t_axis'e (datetime64) doğrusal interpolasyonla taşır; dışını en yakınla doldurur."""
    t = da.time.values
    if t[0] > t_axis[0] or t[-1] < t_axis[-1]:
        log(f"uyarı: CMEMS zaman aralığı {np.datetime_as_string(t[0],'h')}..{np.datetime_as_string(t[-1],'h')} "
            f"istenen {np.datetime_as_string(t_axis[0],'h')}..{np.datetime_as_string(t_axis[-1],'h')} — kenarlar en yakın değerle dolduruldu")
    return da.interp(time=t_axis, kwargs={"fill_value": "extrapolate"}) if len(t) > 1 else da.isel(time=0).expand_dims(time=t_axis)

def write_th(path, arr, dt_s):
    """arr: (time, node, nlev, ncomp) → SCHISM .th.nc"""
    ds = xr.Dataset({"time_step": ((), np.float32(dt_s)),
                     "time": ("time", np.arange(arr.shape[0], dtype="f8") * dt_s),
                     "time_series": (("time", "nOpenBndNodes", "nLevels", "nComponents"), arr.astype("f4"))})
    ds.time.attrs["long_name"] = "seconds since model start (record k = k*time_step)"
    ds.to_netcdf(path, format="NETCDF4")

# ============================================================================ boundary
def cmd_boundary(a):
    run = RUNS / "schism" / a.run
    xyz, opens = read_hgrid(run / "hgrid.gr3")
    bn = np.concatenate(opens); bx, by, bh = xyz[bn, 0], xyz[bn, 1], xyz[bn, 2]
    t0 = np.datetime64(a.start); t1 = np.datetime64(a.end)
    log(f"{len(bn)} açık sınır düğümü; {a.start} → {a.end}; mod {a.mode}")

    # --- su seviyesi (saatlik)
    zos = open_cm("zos")
    iy, ix = nearest_valid_index(zos, bx, by)
    dt_e = 3600.0
    tax = np.arange(t0, t1 + np.timedelta64(1, "h"), np.timedelta64(int(dt_e), "s"))
    z_t = to_regular_time(zos, tax).values  # (time, lat, lon)
    eta = z_t[:, iy, ix] + float(S.get("zos_offset_m", 0.0))
    eta = np.where(np.isfinite(eta), eta, 0.0)
    log(f"elev2D: ortalama {eta.mean():+.3f} m, aralık {eta.min():+.2f}..{eta.max():+.2f} m, {len(tax)} kayıt @ {dt_e:.0f} s")
    write_th(run / "elev2D.th.nc", eta[:, :, None, None], dt_e)
    if a.mode == "2d":
        log("2d: yalnız elev2D.th.nc yazıldı (bctides: 4 0 0 0)"); return

    # --- 3D: sigma seviyeleri
    nvrt, sig, hc, tb, tf = read_vgrid(run / "vgrid.in")
    zlev = z_levels(bh, sig, hc, tb, tf)          # (nb, nvrt), negatif
    dt_3 = float(S.get("bnd3d_dt_s", 21600))
    tax3 = np.arange(t0, t1 + np.timedelta64(1, "h"), np.timedelta64(int(dt_3), "s"))
    def profile_series(var):
        da = open_cm(var)                          # (time, depth, lat, lon), depth pozitif aşağı
        iy, ix = nearest_valid_index(da, bx, by)
        da_t = to_regular_time(da, tax3)           # (time, depth, lat, lon)
        prof = da_t.values[:, :, iy, ix]           # (time, depth, nb)
        dep = da.depth.values
        out = np.empty((len(tax3), len(bn), nvrt), "f4")
        for j in range(len(bn)):
            zq = -zlev[j]                          # pozitif derinlik, yüzey→dip sırası? sig -1..0 → zq dipten yüzeye
            for it in range(len(tax3)):
                col = prof[it, :, j]; ok = np.isfinite(col)
                if ok.sum() == 0: out[it, j, :] = np.nan; continue
                out[it, j, :] = np.interp(zq, dep[ok], col[ok])   # dip altı / yüzey üstü: en yakın (np.interp sabitler)
        # NaN kalan düğüm: komşu düğümden kopyala
        bad = np.isnan(out).any(axis=(0, 2))
        if bad.any():
            good = np.where(~bad)[0]
            for j in np.where(bad)[0]:
                out[:, j, :] = out[:, good[np.argmin(np.abs(good - j))], :]
        return out
    T = profile_series("thetao"); Sa = profile_series("so"); U = profile_series("uo"); V = profile_series("vo")
    log(f"3D sınır: T {np.nanmin(T):.1f}..{np.nanmax(T):.1f} °C, S {np.nanmin(Sa):.1f}..{np.nanmax(Sa):.1f}, "
        f"|u| maks {np.nanmax(np.hypot(U, V)):.2f} m/s; {len(tax3)} kayıt @ {dt_3:.0f} s, nvrt={nvrt}")
    write_th(run / "TEM_3D.th.nc", T[:, :, :, None], dt_3)
    write_th(run / "SAL_3D.th.nc", Sa[:, :, :, None], dt_3)
    write_th(run / "uv3D.th.nc", np.stack([U, V], axis=-1), dt_3)
    # --- başlangıç alanları: yüzey T/S, tüm düğümler (dikeyde tekdüze; ilk sürüm)
    for var, name in [("thetao", "temp.ic"), ("so", "salt.ic")]:
        da = open_cm(var).sel(time=slice(str(t0 - np.timedelta64(1, "D")), None)).isel(time=0)
        top = da.isel(depth=0)
        iy, ix = nearest_valid_index(da.expand_dims("time"), xyz[:, 0], xyz[:, 1])
        val = top.values[iy, ix]
        with open(run / name, "w") as fh:
            fh.write(f"{name} from CMEMS surface\n{0} {len(xyz)}\n")
            for i, v in enumerate(val): fh.write(f"{i+1} {xyz[i,0]:.6f} {xyz[i,1]:.6f} {v:.4f}\n")
        log(f"{name}: {np.nanmin(val):.2f}..{np.nanmax(val):.2f}")

# ============================================================================ sflux
def spec_humidity(d2m_K, p_Pa):
    Td = d2m_K - 273.15
    e = 611.2 * np.exp(17.67 * Td / (Td + 243.5))   # Pa
    return 0.622 * e / (p_Pa - 0.378 * e)

def cmd_sflux(a):
    run = RUNS / "schism" / a.run; sd = run / "sflux"; sd.mkdir(exist_ok=True)
    ds = xr.open_dataset(newest("era5_*.nc"))
    if "valid_time" in ds.dims: ds = ds.rename({"valid_time": "time"})
    for v in ("number", "expver"):
        if v in ds: ds = ds.drop_vars(v)
    if ds.latitude[0] > ds.latitude[-1]: ds = ds.sortby("latitude")
    t0 = np.datetime64(a.start); t1 = np.datetime64(a.end)
    ds = ds.sel(time=slice(t0, t1 + np.timedelta64(1, "D")))
    have = set(ds.data_vars)
    log(f"ERA5: {sorted(have)}; {ds.sizes['time']} saat, grid {ds.sizes['latitude']}x{ds.sizes['longitude']}")
    LON, LAT = np.meshgrid(ds.longitude.values, ds.latitude.values)
    def field(name, default):
        if name in have: return ds[name].values.astype("f4")
        log(f"uyarı: ERA5'te {name} yok, sabit {default} kullanılıyor")
        return np.full((ds.sizes["time"],) + LON.shape, default, "f4")
    u = field("u10", 0.0); v = field("v10", 0.0); p = field("msl", 101325.0); t = field("t2m", 293.15)
    q = spec_humidity(field("d2m", 283.15), p).astype("f4")
    times = ds.time.values
    start = datetime.fromisoformat(a.start)
    ndays = int(np.ceil((t1 - t0) / np.timedelta64(1, "D")))
    for d in range(ndays):
        day0 = t0 + np.timedelta64(d, "D"); day1 = day0 + np.timedelta64(1, "D")
        sel = (times >= day0) & (times <= day1)
        if sel.sum() < 2: log(f"uyarı: gün {d+1} için ERA5 kaydı yetersiz"); continue
        tt = (times[sel] - t0) / np.timedelta64(1, "D")
        out = xr.Dataset(
            {"uwind": (("time", "ny_grid", "nx_grid"), u[sel]), "vwind": (("time", "ny_grid", "nx_grid"), v[sel]),
             "prmsl": (("time", "ny_grid", "nx_grid"), p[sel]), "stmp": (("time", "ny_grid", "nx_grid"), t[sel]),
             "spfh": (("time", "ny_grid", "nx_grid"), q[sel]),
             "lon": (("ny_grid", "nx_grid"), LON.astype("f4")), "lat": (("ny_grid", "nx_grid"), LAT.astype("f4"))},
            coords={"time": ("time", tt.astype("f8"))})
        out.time.attrs = {"long_name": "Time", "standard_name": "time",
                          "units": f"days since {start:%Y-%m-%d}", "base_date": np.array([start.year, start.month, start.day, 0], "i4")}
        out.lon.attrs = {"standard_name": "longitude", "units": "degrees_east"}; out.lat.attrs = {"standard_name": "latitude", "units": "degrees_north"}
        out.uwind.attrs = {"standard_name": "eastward_wind", "units": "m/s"}; out.vwind.attrs = {"standard_name": "northward_wind", "units": "m/s"}
        out.prmsl.attrs = {"standard_name": "air_pressure_at_sea_level", "units": "Pa"}
        out.stmp.attrs = {"standard_name": "air_temperature", "units": "K"}; out.spfh.attrs = {"standard_name": "specific_humidity", "units": "1"}
        out.attrs["Conventions"] = "CF-1.0"
        out.to_netcdf(sd / f"sflux_air_1.{d+1}.nc", format="NETCDF3_CLASSIC")
    (sd / "sflux_inputs.txt").write_text("&sflux_inputs\n/\n")
    spd = np.hypot(u, v)
    log(f"sflux: {ndays} günlük dosya; rüzgâr ort {spd.mean():.1f} m/s, maks {spd.max():.1f} m/s")

# ============================================================================ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["download", "boundary", "sflux", "all"])
    ap.add_argument("--run", default=S.get("run_name", "izmir"))
    ap.add_argument("--start", default="2026-09-06"); ap.add_argument("--end", default="2026-09-13")
    ap.add_argument("--mode", choices=["2d", "3d"], default="2d")
    a = ap.parse_args()
    if a.cmd == "download": cmd_download(a)
    if a.cmd in ("boundary", "all"): cmd_boundary(a)
    if a.cmd in ("sflux", "all"): cmd_sflux(a)

if __name__ == "__main__":
    main()
