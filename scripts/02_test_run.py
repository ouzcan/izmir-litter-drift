"""İlk test koşusu: Bostanlı'dan 100 parçacık, 3 gün, OpenDrift OceanDrift.

Kullanım:
    python scripts/02_test_run.py [YYYY-MM-DD]   # 01_download_sample.py ile aynı başlangıç tarihi
Çıktı: runs/test_bostanli/<tarih>/  (track.nc, track.png, summary.txt)
"""
from __future__ import annotations
import sys
from datetime import datetime, timedelta

from common import RAW, PROC, RUNS, params, point

START = datetime.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime(2026, 9, 6)
P = params()
TR = P["release"]["test_run"]
DUR = timedelta(days=TR["duration_days"])
LON, LAT = point(TR["site"])
OUT = RUNS / "test_bostanli" / f"{START:%Y%m%d}"
OUT.mkdir(parents=True, exist_ok=True)

def newest(pattern, base):
    files = sorted(base.glob(pattern))
    if not files: raise FileNotFoundError(f"{base}/{pattern} yok — önce 01_download_sample.py")
    return files[-1]

def main():
    from opendrift.models.oceandrift import OceanDrift
    from opendrift.readers import reader_netCDF_CF_generic

    cur = reader_netCDF_CF_generic.Reader(str(newest("med_cur_*.nc", RAW)))
    wav = reader_netCDF_CF_generic.Reader(str(newest("med_wav_*.nc", RAW)))
    wnd = reader_netCDF_CF_generic.Reader(str(newest("era5_wind_*.nc", PROC)))

    o = OceanDrift(loglevel=20)
    o.add_reader([cur, wav, wnd])
    o.set_config("general:coastline_action", P["beaching"]["coastline_action"])
    o.set_config("drift:stokes_drift", bool(P["stokes_drift"]))
    # OpenDrift 1.14: yatay difüzyon "environment:fallback:horizontal_diffusivity" ile verilir (m2/s)
    o.set_config("environment:fallback:horizontal_diffusivity", float(P["horizontal_diffusivity_m2s"]["base"]))
    o.set_config("drift:vertical_mixing", False)
    o.set_config("seed:wind_drift_factor", float(P["windage"]["base"]))

    o.seed_elements(lon=LON, lat=LAT, radius=200, number=int(TR["n_particles"]),
                    time=START, wind_drift_factor=float(P["windage"]["base"]))
    o.run(duration=DUR, time_step=int(P["time_step_s"]),
          time_step_output=int(P["output_step_s"]), outfile=str(OUT / "track.nc"))

    o.plot(filename=str(OUT / "track.png"), fast=True, linecolor="age_seconds",
           title=f"Bostanlı test: {TR['n_particles']} parçacık, {TR['duration_days']} gün, windage %{P['windage']['base']*100:.0f}")
    try:
        o.animation(filename=str(OUT / "track.gif"), fast=True)
    except Exception as e:  # noqa: BLE001
        print("animasyon atlandı:", e)

    lines = [str(o), ""]
    try:
        import numpy as np
        ds = o.result                      # xarray Dataset (OpenDrift >= 1.12)
        st = ds["status"].isel(time=-1).values
        names = list(getattr(o, "status_categories", [])) or \
                ds["status"].attrs.get("flag_meanings", "").split()
        counts = {}
        for i in np.unique(st[~np.isnan(st.astype(float))]).astype(int):
            counts[names[i] if i < len(names) else str(i)] = int((st == i).sum())
        lines.append("Son durum: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
        # son geçerli konum (kıyıya vuranlar dahil): zaman ekseninde son NaN olmayan değer
        lon = ds["lon"].ffill("time").isel(time=-1).values
        lat = ds["lat"].ffill("time").isel(time=-1).values
        lines.append(f"Son konum ort: lon {np.nanmean(lon):.4f}, lat {np.nanmean(lat):.4f}; "
                     f"lon aralığı {np.nanmin(lon):.3f}-{np.nanmax(lon):.3f}, lat aralığı {np.nanmin(lat):.3f}-{np.nanmax(lat):.3f}")
    except Exception as e:  # noqa: BLE001
        lines.append(f"özet çıkarılamadı: {e}")
    (OUT / "summary.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[-2:]))
    print("çıktılar:", OUT)

if __name__ == "__main__":
    main()
