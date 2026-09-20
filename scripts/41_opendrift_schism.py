"""OpenDrift (OceanDrift) ile yüzen çöp sürüklenmesi — akıntı: yerel SCHISM koşusu, rüzgâr: ERA5.

Kullanım:
    python scripts/41_opendrift_schism.py --run izmir3d --start 2026-09-06 --days 7 [--site P_bostanli] [--n 500]
    python scripts/41_opendrift_schism.py --run izmir3d --lon 27.094 --lat 38.4515 --days 7
Girdi: runs/schism/<run>/opendrift/schism_surface.nc (40_schism_to_opendrift.py), data/raw/forcing/era5_*.nc
Çıktı: runs/opendrift/<run>_<site>_<tarih>/{track.nc, track.png, summary.txt, zones.csv}

Fizik: yüzey akıntısı (SCHISM en üst sigma) + windage (%2, model_params.yaml) + yatay difüzyon (5 m²/s);
Stokes drift bu sürümde YOK (CMEMS dalga ürünü iç körfezi çözmüyor; sonraki adım: WWM ya da rüzgârdan parametre).
Kıyıya vuran parçacık kalır (stranding); kıyı maskesi GSHHS f (roaring-landmask) — ağın kıyısı da aynı kaynaktan.
"""
from __future__ import annotations
import argparse, csv, glob
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import xarray as xr

from common import ROOT, RAW, PROC, RUNS, CFG, params, point

P = params()
S = P.get("schism", {})

def log(*a): print("[41]", *a, flush=True)

def prepare_wind(start: datetime, end: datetime) -> Path:
    """ERA5 (CDS yeni biçim: valid_time, standard_name 'unknown') → OpenDrift'in okuyacağı CF dosyası."""
    fs = sorted(glob.glob(str(RAW / "forcing" / "era5_*.nc")))
    if not fs: raise SystemExit("data/raw/forcing/era5_*.nc yok — 32_forcing_to_schism.py download")
    ds = xr.open_dataset(fs[-1])
    if "valid_time" in ds.dims: ds = ds.rename({"valid_time": "time"})
    for v in ("number", "expver"):
        if v in ds: ds = ds.drop_vars(v)
    if ds.latitude[0] > ds.latitude[-1]: ds = ds.sortby("latitude")
    ds = ds[["u10", "v10"]].sel(time=slice(np.datetime64(start) - np.timedelta64(1, "h"), np.datetime64(end) + np.timedelta64(2, "h")))
    ds = ds.rename({"u10": "x_wind", "v10": "y_wind"})
    ds["x_wind"].attrs = {"standard_name": "x_wind", "units": "m s-1"}; ds["y_wind"].attrs = {"standard_name": "y_wind", "units": "m s-1"}
    ds["latitude"].attrs = {"standard_name": "latitude", "units": "degrees_north"}; ds["longitude"].attrs = {"standard_name": "longitude", "units": "degrees_east"}
    PROC.mkdir(parents=True, exist_ok=True)
    out = PROC / f"era5_wind_od_{start:%Y%m%d}_{end:%Y%m%d}.nc"
    ds.to_netcdf(out); return out

from od_agg import zones, zone_of   # bölge ataması ortak modülde (kutular sırayla; adalar önce)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=S.get("run_name", "izmir"))
    ap.add_argument("--file", default=None, help="40 ile üretilen dosya (varsayılan runs/schism/<run>/opendrift/schism_surface.nc ya da schism_dav.nc)")
    ap.add_argument("--start", default="2026-09-06"); ap.add_argument("--days", type=float, default=7)
    ap.add_argument("--site", default=P["release"]["test_run"]["site"])
    ap.add_argument("--lon", type=float, default=None); ap.add_argument("--lat", type=float, default=None)
    ap.add_argument("--n", type=int, default=500); ap.add_argument("--radius", type=float, default=200)
    ap.add_argument("--windage", type=float, default=float(P["windage"]["base"]))
    ap.add_argument("--no-wind", action="store_true")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()

    from opendrift.models.oceandrift import OceanDrift
    from opendrift.readers import reader_schism_native, reader_netCDF_CF_generic, reader_global_landmask

    od_dir = RUNS / "schism" / a.run / "opendrift"
    f = Path(a.file) if a.file else (od_dir / "schism_surface.nc" if (od_dir / "schism_surface.nc").exists() else od_dir / "schism_dav.nc")
    if "*" in str(f): first = sorted(glob.glob(str(f)))
    else: first = [f] if f.exists() else []
    if not first: raise SystemExit(f"{f} yok — önce 40_schism_to_opendrift.py --run {a.run}")
    f0 = Path(first[0])                       # statik bilgiler (ağ, derinlik) ilk dosyadan
    start = datetime.fromisoformat(a.start); dur = timedelta(days=a.days)
    if a.lon is None: a.lon, a.lat = point(a.site); site = a.site
    else: site = f"{a.lon:.3f}E_{a.lat:.3f}N"
    out = RUNS / "opendrift" / f"{a.run}_{site}_{start:%Y%m%d}{('_' + a.tag) if a.tag else ''}"
    out.mkdir(parents=True, exist_ok=True)

    cur = reader_schism_native.Reader(filename=str(f), name="schism_" + a.run, use_3d=False)
    log(f"akıntı: {f.name} ({cur.start_time} → {cur.end_time}, adım {cur.time_step}); hız alanı: {xr.open_dataset(f0).attrs.get('velocity_source')}")
    readers = [cur]
    if not a.no_wind:
        wf = prepare_wind(start, start + dur)
        wnd = reader_netCDF_CF_generic.Reader(str(wf)); readers.append(wnd)
        log(f"rüzgâr: {wf.name} ({wnd.start_time} → {wnd.end_time})")
    land = reader_global_landmask.Reader(); readers.append(land)

    import logging; logging.getLogger("opendrift.readers.basereader.unstructured").setLevel(logging.ERROR)
    o = OceanDrift(loglevel=30)
    o.add_reader(readers)
    o.set_config("general:coastline_action", P["beaching"]["coastline_action"])
    o.set_config("general:use_auto_landmask", False)
    o.set_config("drift:stokes_drift", False)
    o.set_config("drift:vertical_mixing", False)
    o.set_config("drift:advection_scheme", "runge-kutta4")
    o.set_config("environment:fallback:horizontal_diffusivity", float(P["horizontal_diffusivity_m2s"]["base"]))
    o.set_config("environment:fallback:x_sea_water_velocity", 0.0); o.set_config("environment:fallback:y_sea_water_velocity", 0.0)
    o.set_config("environment:fallback:x_wind", 0.0); o.set_config("environment:fallback:y_wind", 0.0)
    o.seed_elements(lon=a.lon, lat=a.lat, radius=a.radius, number=a.n, time=start, wind_drift_factor=a.windage)
    o.run(duration=dur, time_step=int(P["time_step_s"]), time_step_output=int(P["output_step_s"]), outfile=str(out / "track.nc"))

    ds = o.result
    lon = ds["lon"].ffill("time").isel(time=-1).values; lat = ds["lat"].ffill("time").isel(time=-1).values
    stat = ds["status"].values.astype(float)                       # (traj, time); pasifleşen parçacıkta sonrası NaN
    names = ds["status"].attrs.get("flag_meanings", "").split(); meaning = {i: n for i, n in enumerate(names)}
    last = np.array([r[np.isfinite(r)][-1] if np.isfinite(r).any() else np.nan for r in stat])
    stranded = np.array([meaning.get(int(v), "?") == "stranded" if np.isfinite(v) else False for v in last])
    tv = ds["time"].values; hours = (tv - tv[0]) / np.timedelta64(1, "h")
    t_end = np.array([hours[np.where(np.isfinite(r))[0][-1]] if np.isfinite(r).any() else np.nan for r in stat])
    Z = zones(); zc = {}
    for x, y, sflag in zip(lon, lat, stranded):
        if not np.isfinite(x): continue
        zid, name = zone_of(x, y, Z)
        key = (zid, name, "kıyıda" if sflag else "denizde/alan dışı")
        zc[key] = zc.get(key, 0) + 1
    n = int(np.isfinite(lon).sum())
    lines = [f"koşu: {a.run} | {site} ({a.lon:.4f}E {a.lat:.4f}N) | {start:%Y-%m-%d} +{a.days:g} gün | {a.n} parçacık | windage {a.windage} | rüzgâr {'yok' if a.no_wind else 'ERA5'}",
             f"süre: {hours[-1]:.0f} saat simüle edildi ({len(tv)} çıktı adımı)",
             "son durum: " + ", ".join(f"{meaning.get(int(k), k)}={int((last == k).sum())}" for k in np.unique(last[np.isfinite(last)])),
             f"kıyıya vuran: {int(stranded.sum())}/{n} (%{100*stranded.sum()/max(n,1):.0f})"]
    if stranded.any():
        ts = t_end[stranded]
        lines.append(f"kıyıya vurma süresi (saat): medyan {np.median(ts):.1f}, %25-%75 {np.percentile(ts,25):.1f}-{np.percentile(ts,75):.1f}, ilk {np.min(ts):.1f}, son {np.max(ts):.1f}")
    lines += ["", "bölge dağılımı (son konum):"]
    with open(out / "zones.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh); w.writerow(["zone_id", "zone", "durum", "n", "pay"])
        for (zid, name, sflag), c in sorted(zc.items(), key=lambda kv: -kv[1]):
            w.writerow([zid, name, sflag, c, f"{c/n:.3f}"]); lines.append(f"  {zid} {name:24s} {sflag:18s} {c:5d}  %{100*c/n:.0f}")
    # parçacık bazlı son konum tablosu (web sitesi / toplulaştırma için)
    with open(out / "endpoints.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh); w.writerow(["id", "lon_end", "lat_end", "stranded", "t_end_h", "zone_id"])
        for i in range(len(lon)):
            if np.isfinite(lon[i]): w.writerow([i, f"{lon[i]:.5f}", f"{lat[i]:.5f}", int(stranded[i]), f"{t_end[i]:.1f}", zone_of(lon[i], lat[i], Z)[0]])
    (out / "summary.txt").write_text("\n".join(lines), encoding="utf-8"); print("\n".join(lines))
    try:
        allon = ds["lon"].values; allat = ds["lat"].values
        pad = 0.03; c = [np.nanmin(allon) - pad, np.nanmax(allon) + pad, np.nanmin(allat) - pad, np.nanmax(allat) + pad]
        c = [max(c[0], 26.25), min(c[1], 27.25), max(c[2], 38.28), min(c[3], 38.95)]
        o.plot(filename=str(out / "track.png"), fast=False, linecolor="age_seconds", corners=c,
               title=f"{site}: {a.n} parçacık, {a.days:g} gün, SCHISM {a.run} + ERA5, windage %{a.windage*100:.0f}")
    except Exception as e:  # noqa: BLE001
        log("çizim atlandı:", e)
    log("çıktılar:", out)

if __name__ == "__main__":
    main()
