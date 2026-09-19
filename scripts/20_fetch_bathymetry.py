"""EMODnet Bathymetry DTM 2024 (1/16 arcmin ≈ 115 m) indir — çalışma alanı A + tampon.

Kaynak: EMODnet ERDDAP, dataset 'bathymetry_dtm_2024', değişken 'elevation'
(metre, LAT referanslı; Ege'de LAT ≈ OSD − 0,15 m, ihmal edilebilir).

Kullanım (kullanıcının bilgisayarında):
    python scripts/20_fetch_bathymetry.py
Çıktı: data/raw/bathy/emodnet_dtm2024_A.nc  + data/processed/bathy_quicklook.png
"""
from __future__ import annotations
import sys
import urllib.request
from pathlib import Path

from common import RAW, PROC, bbox

DATASET_CANDIDATES = ["bathymetry_dtm_2024", "bathymetry_2022", "emodnet_bathy_2020_full"]
BUFFER = 0.15  # derece

def fetch(dataset: str, lon0, lon1, lat0, lat1, out: Path) -> bool:
    url = (f"https://erddap.emodnet.eu/erddap/griddap/{dataset}.nc"
           f"?elevation[({lat0}):({lat1})][({lon0}):({lon1})]")
    print(f"[indir] {dataset}\n        {url}")
    try:
        with urllib.request.urlopen(url, timeout=600) as r, open(out, "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[hata] {dataset}: {e}")
        if out.exists():
            out.unlink()
        return False

def main():
    lon0, lon1, lat0, lat1 = bbox("A_il_kiyisi")
    lon0 -= BUFFER; lat0 -= BUFFER; lon1 += BUFFER; lat1 += BUFFER
    outdir = RAW / "bathy"; outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / "emodnet_dtm2024_A.nc"
    if out.exists():
        print(f"[atla] {out} zaten var")
    else:
        for ds in DATASET_CANDIDATES:
            if fetch(ds, lon0, lon1, lat0, lat1, out):
                break
        else:
            sys.exit("EMODnet indirilemedi. Alternatif: https://download.gebco.net adresinden "
                     f"lon {lon0:.2f}-{lon1:.2f}, lat {lat0:.2f}-{lat1:.2f} için netCDF indirip "
                     "data/raw/bathy/gebco_A.nc olarak kaydet.")

    import xarray as xr, numpy as np
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ds = xr.open_dataset(out)
    el = ds["elevation"]
    print(f"[ok] boyut {dict(el.sizes)}, lat {float(el.latitude.min()):.3f}-{float(el.latitude.max()):.3f}, "
          f"lon {float(el.longitude.min()):.3f}-{float(el.longitude.max()):.3f}, "
          f"adım {float(el.latitude[1]-el.latitude[0]):.5f}°")
    sea = el.where(el < 0)
    ic = sea.sel(latitude=slice(38.38, 38.50), longitude=slice(27.00, 27.20))
    print(f"[ok] iç körfez: {int(np.isfinite(ic.values).sum())} deniz hücresi, "
          f"medyan derinlik {float(-ic.median()):.1f} m, maks {float(-ic.min()):.1f} m")
    fig, ax = plt.subplots(figsize=(9, 8))
    sea.plot(ax=ax, vmin=-120, vmax=0, cmap="Blues_r", cbar_kwargs={"label": "m (LAT)"})
    ax.set_title("EMODnet DTM 2024 — İzmir il kıyısı"); ax.set_aspect(1/np.cos(np.deg2rad(38.5)))
    PROC.mkdir(parents=True, exist_ok=True)
    fig.savefig(PROC / "bathy_quicklook.png", dpi=110, bbox_inches="tight")
    print("[yaz]", PROC / "bathy_quicklook.png")

if __name__ == "__main__":
    main()
