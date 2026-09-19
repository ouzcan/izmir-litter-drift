"""OSM kara poligonlarını indir ve çalışma alanına kes (kıyı çizgisi, ~10 m doğruluk).

Kaynak: https://osmdata.openstreetmap.de/data/land-polygons.html  (WGS84, split)
Dosya ~700 MB; bir kez iner, data/raw/osm/ altında kalır (git dışı).
Çıktı: data/processed/osm_land_izmir.gpkg  (+ png)

GSHHS 'f' (~200 m) yedek olarak dfm_tools içinde zaten var; bu betik isteğe bağlı ama
iç körfez için 100 m'lik ağda liman/mendirek ayrıntısı OSM'den gelir.
"""
from __future__ import annotations
import urllib.request, zipfile
from pathlib import Path

from common import RAW, PROC, bbox

URL = "https://osmdata.openstreetmap.de/download/land-polygons-split-4326.zip"
BUFFER = 0.1

def main():
    import geopandas as gpd
    lon0, lon1, lat0, lat1 = bbox("A_il_kiyisi")
    lon0 -= BUFFER; lat0 -= BUFFER; lon1 += BUFFER; lat1 += BUFFER
    outdir = RAW / "osm"; outdir.mkdir(parents=True, exist_ok=True)
    zpath = outdir / "land-polygons-split-4326.zip"
    if not zpath.exists():
        print(f"[indir] {URL} (~700 MB)")
        urllib.request.urlretrieve(URL, zpath)
    shp = next(outdir.rglob("land_polygons.shp"), None)
    if shp is None:
        print("[aç]", zpath)
        with zipfile.ZipFile(zpath) as z:
            z.extractall(outdir)
        shp = next(outdir.rglob("land_polygons.shp"))
    print("[oku] bbox ile", shp)
    gdf = gpd.read_file(shp, bbox=(lon0, lat0, lon1, lat1))
    gdf = gdf.clip((lon0, lat0, lon1, lat1)).explode(index_parts=False).reset_index(drop=True)
    gdf = gdf[gdf.geometry.geom_type == "Polygon"]
    gdf["area_km2"] = gdf.to_crs(3035).area / 1e6
    PROC.mkdir(parents=True, exist_ok=True)
    out = PROC / "osm_land_izmir.gpkg"
    gdf.to_file(out, driver="GPKG")
    print(f"[yaz] {out}: {len(gdf)} poligon, toplam {gdf.area_km2.sum():.0f} km²")
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    ax = gdf.plot(figsize=(9, 8), color="0.7", edgecolor="k", linewidth=0.3)
    ax.set_xlim(26.3, 27.25); ax.set_ylim(38.3, 38.9); ax.set_title("OSM kara poligonları — körfez")
    plt.savefig(PROC / "osm_land_korfez.png", dpi=110, bbox_inches="tight")

if __name__ == "__main__":
    main()
