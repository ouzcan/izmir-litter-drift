"""1 haftalık örnek zorlama verisi indir: MED akıntı + dalga (Copernicus Marine), ERA5 rüzgâr (CDS).

Kullanım (Windows, conda 'litter' ortamı):
    copernicusmarine login          # bir kez
    python scripts/01_download_sample.py [YYYY-MM-DD] [gün sayısı]

Not: Copernicus/CDS sunucularına Claude'un ortamlarından erişilemiyor; bu betik
kullanıcının bilgisayarında çalışır. Çıktılar data/raw ve data/processed altına yazılır.
"""
from __future__ import annotations
import sys
from datetime import datetime, timedelta
from pathlib import Path

from common import RAW, PROC, bbox, params

START = datetime.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime(2026, 9, 6)
DAYS = int(sys.argv[2]) if len(sys.argv) > 2 else 7
END = START + timedelta(days=DAYS)
LON0, LON1, LAT0, LAT1 = bbox("A_il_kiyisi")
TAG = f"{START:%Y%m%d}_{END:%Y%m%d}"
RAW.mkdir(parents=True, exist_ok=True); PROC.mkdir(parents=True, exist_ok=True)
P = params()["forcing"]

def cmems(dataset_id: str, variables: list[str], out: Path, surface_only: bool):
    import copernicusmarine as cm
    if out.exists():
        print(f"[atla] {out.name} zaten var"); return
    kw = dict(dataset_id=dataset_id, variables=variables,
              minimum_longitude=LON0, maximum_longitude=LON1,
              minimum_latitude=LAT0, maximum_latitude=LAT1,
              start_datetime=START.isoformat(), end_datetime=END.isoformat(),
              output_filename=out.name, output_directory=str(out.parent))
    if surface_only:
        kw.update(minimum_depth=0, maximum_depth=1.5)
    print(f"[indir] {dataset_id} -> {out.name}")
    cm.subset(**kw)

def era5(out_raw: Path, out_proc: Path):
    import cdsapi, xarray as xr, numpy as np
    if not out_raw.exists():
        days = sorted({(START + timedelta(days=i)).day for i in range(DAYS + 1)})
        months = sorted({(START + timedelta(days=i)).month for i in range(DAYS + 1)})
        years = sorted({(START + timedelta(days=i)).year for i in range(DAYS + 1)})
        req = {
            "product_type": ["reanalysis"],
            "variable": ["10m_u_component_of_wind", "10m_v_component_of_wind"],
            "year": [f"{y}" for y in years], "month": [f"{m:02d}" for m in months],
            "day": [f"{d:02d}" for d in days],
            "time": [f"{h:02d}:00" for h in range(24)],
            "area": [LAT1, LON0, LAT0, LON1],   # N, W, S, E
            "data_format": "netcdf", "download_format": "unarchived",
        }
        print(f"[indir] ERA5 u10/v10 -> {out_raw.name} (kuyruk birkaç dakika sürebilir)")
        cdsapi.Client().retrieve("reanalysis-era5-single-levels", req, str(out_raw))
    else:
        print(f"[atla] {out_raw.name} zaten var")
    # OpenDrift için normalize et: time boyutu, artan enlem, standard_name
    ds = xr.open_dataset(out_raw)
    if "valid_time" in ds.dims: ds = ds.rename({"valid_time": "time"})
    if "latitude" in ds.coords and ds.latitude[0] > ds.latitude[-1]:
        ds = ds.sortby("latitude")
    ds = ds.sel(time=slice(START, END))
    ds["u10"].attrs.update(standard_name="x_wind", units="m s-1")
    ds["v10"].attrs.update(standard_name="y_wind", units="m s-1")
    for v in ("number", "expver"):
        if v in ds: ds = ds.drop_vars(v)
    ds.to_netcdf(out_proc); ds.close()
    print(f"[yaz] {out_proc.name}")

if __name__ == "__main__":
    print(f"Alan A: lon {LON0}-{LON1}, lat {LAT0}-{LAT1}; {START:%Y-%m-%d} -> {END:%Y-%m-%d}")
    cmems(P["currents"], ["uo", "vo"], RAW / f"med_cur_{TAG}.nc", surface_only=True)
    cmems(P["waves"], ["VSDX", "VSDY", "VHM0"], RAW / f"med_wav_{TAG}.nc", surface_only=False)
    era5(RAW / f"era5_wind_{TAG}.nc", PROC / f"era5_wind_{TAG}.nc")
    print("bitti")
