"""Yıllık OpenDrift salımları — aylık partiler (SCHISM yüzey alanı data/processed/schism_surface_*.nc + ERA5).

Her ay için ayrı bir OpenDrift koşusu: ay boyunca salınan parçacıklar en çok --track_days gün izlenir (koşu ay sonu + track_days
ile biter; sonraki ayların yüzey dosyaları varsa okunur). İki salım şeması:
  sources : config/sources.csv kaynakları, her --pulse_h saatte --n_src parçacık (varsayılan 6 saat × 10)
  grid    : --cell_km ızgarası, haftada bir (--grid_every_days) --n_grid parçacık (varsayılan 7 gün × 10)
Çıktı: runs/opendrift/year/<mode>_<YYYY-MM>/{endpoints.csv, origins.csv, meta.json, matrix.csv, summary.txt}
       (52_seasonal_maps.py bunları mevsim/yıl bazında birleştirir)

Kullanım (Windows, litter):
    python scripts/51_year_opendrift.py --mode sources            # hazır olan tüm aylar (yüzey dosyası varsa)
    python scripts/51_year_opendrift.py --mode grid --month 2025-09
    python scripts/51_year_opendrift.py --mode both --windage 0.01 --tag w1   # duyarlılık
Yüzey dosyası olmayan aylar atlanır; biten aylar (endpoints.csv var) --force olmadan tekrar koşulmaz.
"""
from __future__ import annotations
import argparse, csv, glob, importlib, json
from datetime import date, datetime, timedelta
from pathlib import Path
import numpy as np
import xarray as xr

from common import ROOT, RUNS, PROC, CFG, params, bbox
import od_agg as agg
m41 = importlib.import_module("41_opendrift_schism")
m42 = importlib.import_module("42_release_matrix")

P = params(); Y = P.get("year_run", {})
COSLAT = np.cos(np.deg2rad(38.5))

def log(*a): print("[51]", *a, flush=True)

def month_list(a):
    start = date.fromisoformat(str(Y.get("start", "2025-09-01"))); end = date.fromisoformat(str(Y.get("end", "2026-09-01")))
    out = []; d = start
    while d < end:
        nxt = (d.replace(day=28) + timedelta(days=4)).replace(day=1); out.append((f"{d:%Y-%m}", d, min(nxt, end))); d = nxt
    if a.month: out = [m for m in out if m[0] == a.month]
    return out

def surface_files(m0: date, m1: date, track_days: int):
    """Ay + izleme süresi için gereken yüzey dosyaları (ay dosyası zorunlu, sonrakiler varsa)."""
    need = []; d = m0
    while d < m1 + timedelta(days=track_days):
        need.append(f"{d:%Y-%m}"); d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    have = [PROC / f"schism_surface_{ym}.nc" for ym in need if (PROC / f"schism_surface_{ym}.nc").exists()]
    return have, need

def build_origins(mode, f0, x0, x1, y0, y1, cell_km):
    sx, sy = m42.sea_nodes(f0)
    if mode == "sources":
        src, skipped = m42.read_sources(x0, x1, y0, y1)
        lon_s, lat_s, dist = m42.snap(np.array([s[2] for s in src]), np.array([s[3] for s in src]), sx, sy, max_km=2.5)
        org = [{"origin": s[0], "name": s[1], "lon": float(lon_s[k]), "lat": float(lat_s[k])} for k, s in enumerate(src) if np.isfinite(lon_s[k])]
        return org, 150.0
    dx = cell_km / (111.0 * COSLAT); dy = cell_km / 111.0
    gx = np.arange(x0 + dx / 2, x1, dx); gy = np.arange(y0 + dy / 2, y1, dy)
    GX, GY = np.meshgrid(gx, gy); GX = GX.ravel(); GY = GY.ravel()
    _, _, dist = m42.snap(GX, GY, sx, sy, max_km=99); keep = dist <= 0.6 * cell_km
    KX, KY = GX[keep], GY[keep]
    org = [{"origin": f"C{k:05d}", "name": f"C{k:05d}", "lon": float(KX[k]), "lat": float(KY[k])} for k in range(KX.size)]
    return org, cell_km * 300.0

def run_month(a, mode, ym, m0, m1):
    out = RUNS / "opendrift" / "year" / f"{mode}_{ym}{('_' + a.tag) if a.tag else ''}"
    if (out / "endpoints.csv").exists() and not a.force: log(mode, ym, "bitmiş, atla"); return
    files, need = surface_files(m0, m1, a.track_days)
    if not (PROC / f"schism_surface_{ym}.nc").exists(): log(mode, ym, "yüzey dosyası yok, atla"); return
    yend = date.fromisoformat(str(Y.get("end", "2026-09-01")))
    eksik = [q for q in need if not (PROC / f"schism_surface_{q}.nc").exists() and date.fromisoformat(q + "-01") < yend]
    if eksik and not a.allow_truncated:
        log(mode, ym, f"izleme ayı eksik ({', '.join(eksik)}) → ay sonunda salınanlar takip edilemez, atla (--allow_truncated ile yine de koş)"); return
    out.mkdir(parents=True, exist_ok=True)
    from opendrift.models.oceandrift import OceanDrift
    from opendrift.readers import reader_schism_native, reader_netCDF_CF_generic, reader_global_landmask
    import logging; logging.getLogger("opendrift.readers.basereader.unstructured").setLevel(logging.ERROR)
    x0, x1, y0, y1 = bbox("B_model")
    origins, radius = build_origins(mode, files[0], x0, x1, y0, y1, a.cell_km)
    t0 = datetime(m0.year, m0.month, m0.day); t1 = datetime(m1.year, m1.month, m1.day)
    if mode == "sources":
        times = [t0 + timedelta(hours=float(h)) for h in np.arange(0.0, (t1 - t0).total_seconds() / 3600.0, float(a.pulse_h))]; n_per = a.n_src
    else:
        times = [t0 + timedelta(days=float(d)) for d in np.arange(0.0, float((t1 - t0).days), float(a.grid_every_days))]; n_per = a.n_grid
    cur = reader_schism_native.Reader(filename=[str(f) for f in files] if len(files) > 1 else str(files[0]), name="schism_year", use_3d=False)
    end = min(t1 + timedelta(days=a.track_days), cur.end_time)
    readers = [cur]
    if not a.no_wind: readers.append(reader_netCDF_CF_generic.Reader(str(m41.prepare_wind(t0, end))))
    readers.append(reader_global_landmask.Reader())
    o = OceanDrift(loglevel=30); o.add_reader(readers)
    o.set_config("general:coastline_action", P["beaching"]["coastline_action"]); o.set_config("general:use_auto_landmask", False)
    o.set_config("drift:stokes_drift", False); o.set_config("drift:vertical_mixing", False); o.set_config("drift:advection_scheme", "runge-kutta4")
    o.set_config("environment:fallback:horizontal_diffusivity", float(a.diffusivity))
    for v in ("x_sea_water_velocity", "y_sea_water_velocity", "x_wind", "y_wind"): o.set_config(f"environment:fallback:{v}", 0.0)
    for k, og in enumerate(origins):
        for t in times:
            o.seed_elements(lon=og["lon"], lat=og["lat"], radius=radius, number=n_per, time=t, wind_drift_factor=a.windage, origin_marker=k)
    ntot = len(origins) * len(times) * n_per
    log(f"{mode} {ym}: {len(origins)} nokta × {len(times)} salım × {n_per} = {ntot} parçacık; akıntı {files[0].name}..{files[-1].name}; bitiş {end:%Y-%m-%d}")
    o.run(end_time=end, time_step=int(P["time_step_s"]), time_step_output=3600 * 3, outfile=str(out / "track.nc"))
    with open(out / "origins.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["origin", "name", "lon", "lat"]); w.writeheader()
        for og in origins: w.writerow({**og, "lon": f"{og['lon']:.5f}", "lat": f"{og['lat']:.5f}"})
    meta = {"mode": mode, "run": "year", "month": ym, "start": t0.isoformat(), "end": end.isoformat(), "days": (end - t0).days,
            "windage": a.windage, "diffusivity": a.diffusivity, "wind": not a.no_wind, "cell_km": a.cell_km, "track_days": a.track_days,
            "n_particles": ntot, "header": f"yıl {mode} {ym} | {ntot} parçacık | windage {a.windage} | difüzyon {a.diffusivity} | rüzgâr {'yok' if a.no_wind else 'ERA5'}"}
    json.dump(meta, open(out / "meta.json", "w", encoding="utf-8"), ensure_ascii=False)
    ep = agg.endpoints_from_result(o.result)
    # salım zamanı mutlak (saat, ay başından) zaten t_rel'de; matris/summary aylık
    agg.aggregate(out, origins, ep, meta)
    if not a.keep_track:
        try: (out / "track.nc").unlink()
        except OSError: pass
    log("çıktılar:", out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["sources", "grid", "both"], default="both")
    ap.add_argument("--month", default=None); ap.add_argument("--force", action="store_true")
    ap.add_argument("--track_days", type=int, default=int(Y.get("track_days", 30)))
    ap.add_argument("--pulse_h", type=float, default=6); ap.add_argument("--n_src", type=int, default=10)
    ap.add_argument("--grid_every_days", type=float, default=7); ap.add_argument("--n_grid", type=int, default=10)
    ap.add_argument("--cell_km", type=float, default=1.0)
    ap.add_argument("--windage", type=float, default=float(P["windage"]["base"])); ap.add_argument("--no-wind", action="store_true")
    ap.add_argument("--diffusivity", type=float, default=float(P["horizontal_diffusivity_m2s"]["base"]))
    ap.add_argument("--tag", default=""); ap.add_argument("--keep_track", action="store_true", help="track.nc'yi sakla (büyük)")
    ap.add_argument("--allow_truncated", action="store_true", help="sonraki ayın yüzey dosyası yokken de koş (izleme ay sonunda kesilir)")
    a = ap.parse_args()
    modes = ["sources", "grid"] if a.mode == "both" else [a.mode]
    for ym, m0, m1 in month_list(a):
        for mode in modes: run_month(a, mode, ym, m0, m1)

if __name__ == "__main__":
    main()
