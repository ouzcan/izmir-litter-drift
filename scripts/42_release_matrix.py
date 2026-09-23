"""Kaynak → kıyı bağlantı matrisi: çok kaynaklı / ızgara salımlı OpenDrift koşusu (SCHISM yüzey akıntısı + ERA5).

Kullanım:
    python scripts/42_release_matrix.py --run izmir3d --start 2026-09-06 --days 7 --mode sources
    python scripts/42_release_matrix.py --run izmir3d --start 2026-09-06 --days 7 --mode grid --cell_km 1
Salım: `sources` → config/sources.csv'deki koordinatlı kaynaklar (alan içindekiler), ilk --release_days gün boyunca her
       --pulse_h saatte bir --n parçacık; `grid` → --cell_km aralıklı deniz hücreleri (web sitesi "nereden atarsam" katmanı),
       --pulses adet salım (t0, t0+24h, …). Karadaki/çok sığ noktalar en yakın ≥2 m derinlikli ağ düğümüne kaydırılır.
Çıktı: runs/opendrift/matrix_<run>_<mode>_<tarih>/{matrix.csv, endpoints.csv, cells.geojson (grid), matrix.png, summary.txt}
"""
from __future__ import annotations
import argparse, csv, glob, json
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import xarray as xr

from common import RUNS, CFG, params, bbox
import importlib
m41 = importlib.import_module("41_opendrift_schism")
import od_agg as agg

P = params(); S = P.get("schism", {})
COSLAT = np.cos(np.deg2rad(38.5))

def log(*a): print("[42]", *a, flush=True)

def sea_nodes(f: Path, min_depth=2.0):
    d = xr.open_dataset(f, decode_times=False)
    x = d.SCHISM_hgrid_node_x.values; y = d.SCHISM_hgrid_node_y.values; h = d.depth.values
    ok = h >= min_depth
    return x[ok], y[ok]

def snap(lon, lat, sx, sy, max_km=2.0):
    """Noktayı en yakın deniz düğümüne kaydır (kara/sığ salımı önlemek için)."""
    from scipy.spatial import cKDTree
    tree = cKDTree(np.c_[sx * COSLAT * 111.0, sy * 111.0])
    d, i = tree.query(np.c_[np.atleast_1d(lon) * COSLAT * 111.0, np.atleast_1d(lat) * 111.0])
    lon2 = np.where(d <= max_km, sx[i], np.nan); lat2 = np.where(d <= max_km, sy[i], np.nan)
    return lon2, lat2, d

def read_sources(x0, x1, y0, y1):
    rows = list(csv.DictReader(open(CFG / "sources.csv", encoding="utf-8")))
    out, skipped = [], []
    for r in rows:
        try: lon, lat = float(r["lon"]), float(r["lat"])
        except ValueError: skipped.append(f"{r['id']} (koordinat yok)"); continue
        if not (x0 <= lon <= x1 and y0 <= lat <= y1): skipped.append(f"{r['id']} (alan dışı)"); continue
        out.append((r["id"], r["name"], lon, lat))
    return out, skipped

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=S.get("run_name", "izmir")); ap.add_argument("--file", default=None)
    ap.add_argument("--start", default="2026-09-06"); ap.add_argument("--days", type=float, default=7)
    ap.add_argument("--mode", choices=["sources", "grid"], default="sources")
    ap.add_argument("--n", type=int, default=None, help="salım başına parçacık (sources: 50, grid: 20)")
    ap.add_argument("--pulse_h", type=float, default=6); ap.add_argument("--release_days", type=float, default=3)
    ap.add_argument("--pulses", type=int, default=3, help="grid: salım sayısı (24 saat arayla)")
    ap.add_argument("--cell_km", type=float, default=1.0)
    ap.add_argument("--windage", type=float, default=float(P["windage"]["base"])); ap.add_argument("--no-wind", action="store_true")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    from opendrift.models.oceandrift import OceanDrift
    from opendrift.readers import reader_schism_native, reader_netCDF_CF_generic, reader_global_landmask
    import logging; logging.getLogger("opendrift.readers.basereader.unstructured").setLevel(logging.ERROR)

    od_dir = RUNS / "schism" / a.run / "opendrift"
    f = Path(a.file) if a.file else (od_dir / "schism_surface.nc" if (od_dir / "schism_surface.nc").exists() else od_dir / "schism_dav.nc")
    if "*" in str(f): first = sorted(glob.glob(str(f)))
    else: first = [f] if f.exists() else []
    if not first: raise SystemExit(f"{f} yok — önce 40_schism_to_opendrift.py --run {a.run}")
    f0 = Path(first[0])                       # statik bilgiler (ağ, derinlik) ilk dosyadan
    start = datetime.fromisoformat(a.start); dur = timedelta(days=a.days)
    x0, x1, y0, y1 = bbox("B_model")
    out = RUNS / "opendrift" / f"matrix_{a.run}_{a.mode}_{start:%Y%m%d}{('_' + a.tag) if a.tag else ''}"; out.mkdir(parents=True, exist_ok=True)
    sx, sy = sea_nodes(f0)

    # --- salım noktaları
    if a.mode == "sources":
        n_per = a.n or 50
        src, skipped = read_sources(x0, x1, y0, y1)
        if skipped: log("atlanan kaynaklar:", ", ".join(skipped))
        ids = [s[0] for s in src]; names = {s[0]: s[1] for s in src}
        lon0 = np.array([s[2] for s in src]); lat0 = np.array([s[3] for s in src])
        lon_s, lat_s, dist = snap(lon0, lat0, sx, sy, max_km=2.5)
        for k, (i, d) in enumerate(zip(ids, dist)):
            if not np.isfinite(lon_s[k]): log(f"  {i} atlandı: en yakın ≥2 m düğüm {d:.1f} km ötede")
            elif d > 0.3: log(f"  {i} denize kaydırıldı: {d*1000:.0f} m")
        times = [start + timedelta(hours=h) for h in np.arange(0, a.release_days * 24 + 1e-9, a.pulse_h)]
        pts = [(k, lon_s[k], lat_s[k], t) for k in range(len(ids)) for t in times if np.isfinite(lon_s[k])]
        radius = 150
    else:
        n_per = a.n or 20
        dx = a.cell_km / (111.0 * COSLAT); dy = a.cell_km / 111.0
        gx = np.arange(x0 + dx / 2, x1, dx); gy = np.arange(y0 + dy / 2, y1, dy)
        GX, GY = np.meshgrid(gx, gy); GX = GX.ravel(); GY = GY.ravel()
        _, _, dist = snap(GX, GY, sx, sy, max_km=99)
        keep = dist <= 0.6 * a.cell_km            # hücre merkezi denize yakın (≥2 m derinlikli düğüm)
        GX, GY = GX[keep], GY[keep]
        ids = [f"C{k:05d}" for k in range(len(GX))]; names = {i: i for i in ids}
        lon_s, lat_s = GX, GY
        times = [start + timedelta(days=p) for p in range(a.pulses)]
        pts = [(k, GX[k], GY[k], t) for k in range(len(ids)) for t in times]
        radius = a.cell_km * 300
        log(f"ızgara: {len(gx)}×{len(gy)} → {len(GX)} deniz hücresi ({a.cell_km} km)")
    log(f"{len(ids)} salım noktası × {len(times)} salım × {n_per} parçacık = {len(pts) * n_per}")

    # --- okuyucular ve koşu
    cur = reader_schism_native.Reader(filename=str(f), name="schism_" + a.run, use_3d=False)
    readers = [cur]
    if not a.no_wind: readers.append(reader_netCDF_CF_generic.Reader(str(m41.prepare_wind(start, start + dur))))
    readers.append(reader_global_landmask.Reader())
    o = OceanDrift(loglevel=30); o.add_reader(readers)
    o.set_config("general:coastline_action", P["beaching"]["coastline_action"]); o.set_config("general:use_auto_landmask", False)
    o.set_config("drift:stokes_drift", False); o.set_config("drift:vertical_mixing", False); o.set_config("drift:advection_scheme", "runge-kutta4")
    o.set_config("environment:fallback:horizontal_diffusivity", float(P["horizontal_diffusivity_m2s"]["base"]))
    for v in ("x_sea_water_velocity", "y_sea_water_velocity", "x_wind", "y_wind"): o.set_config(f"environment:fallback:{v}", 0.0)
    for k, lo, la, t in pts:
        o.seed_elements(lon=lo, lat=la, radius=radius, number=n_per, time=t, wind_drift_factor=a.windage, origin_marker=k)
    o.run(duration=dur, time_step=int(P["time_step_s"]), time_step_output=3600 * 3, outfile=str(out / "track.nc"))

    # --- toplulaştırma (od_agg ortak modülü; 43_rezone.py aynı işlevi endpoints.csv'den tekrar yapar)
    origins = [{"origin": ids[k], "name": names[ids[k]], "lon": lon_s[k], "lat": lat_s[k]} for k in range(len(ids))]
    with open(out / "origins.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["origin", "name", "lon", "lat"]); w.writeheader()
        for og in origins: w.writerow({**og, "lon": f"{og['lon']:.5f}", "lat": f"{og['lat']:.5f}"})
    meta = {"mode": a.mode, "run": a.run, "start": a.start, "days": a.days, "windage": a.windage, "cell_km": a.cell_km,
            "header": f"koşu: {a.run} | {a.mode} | {start:%Y-%m-%d} +{a.days:g} gün | {len(ids)} nokta, {len(pts)*n_per} parçacık | windage {a.windage} | rüzgâr {'yok' if a.no_wind else 'ERA5'}"}
    json.dump(meta, open(out / "meta.json", "w", encoding="utf-8"), ensure_ascii=False)
    ep = agg.endpoints_from_result(o.result, model=o)
    rows, zone, zn = agg.aggregate(out, origins, ep, meta)
    try: agg.plot_matrix(out, origins, ep, rows, zn, meta, coast_file=f0)
    except Exception as e:  # noqa: BLE001
        log("çizim atlandı:", e)
    log("çıktılar:", out)

if __name__ == "__main__":
    main()
