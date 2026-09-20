"""Var olan bir 42 koşusunu (endpoints.csv + origins.csv/cells.geojson) OpenDrift'i tekrar koşturmadan,
güncel config/coast_zones.csv ile yeniden toplulaştır: matrix.csv, summary.txt, cells.geojson, matrix.png yenilenir.

Kullanım:
    python scripts/43_rezone.py --dir runs/opendrift/matrix_izmir3d_grid_20260906
"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path

from common import RUNS
import od_agg as agg

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dir", required=True); ap.add_argument("--coast", default=None, help="kıyı çizgisi için 40 dosyası (schism_surface.nc)")
    a = ap.parse_args(); out = Path(a.dir)
    if not out.is_absolute(): out = (RUNS.parent / out) if not out.exists() else out
    meta = json.load(open(out / "meta.json", encoding="utf-8")) if (out / "meta.json").exists() else {}
    if (out / "origins.csv").exists():
        origins = list(csv.DictReader(open(out / "origins.csv", encoding="utf-8")))
    elif (out / "cells.geojson").exists():          # eski koşu (origins.csv yok): hücre merkezleri geojson'dan
        g = json.load(open(out / "cells.geojson", encoding="utf-8"))
        origins = [{"origin": f["properties"]["origin"], "name": f["properties"].get("name", f["properties"]["origin"]),
                    "lon": f["geometry"]["coordinates"][0], "lat": f["geometry"]["coordinates"][1]} for f in g["features"]]
        meta.setdefault("mode", "grid"); meta.setdefault("cell_km", g.get("cell_km", 1.0))
        for k in ("run", "start", "days"): meta.setdefault(k, g.get(k, ""))
    else:                                           # eski kaynak koşusu: matrix.csv'den
        origins = [{"origin": r["origin"], "name": r["name"], "lon": r["lon"], "lat": r["lat"]} for r in csv.DictReader(open(out / "matrix.csv", encoding="utf-8"))]
        meta.setdefault("mode", "sources")
    if "header" not in meta:
        meta["header"] = (out / "summary.txt").read_text(encoding="utf-8").splitlines()[0] if (out / "summary.txt").exists() else out.name
    if (out / "endpoints.csv").exists():
        ep = agg.endpoints_from_csv(out / "endpoints.csv", origins)
    else:                                           # toplulaştırma yarıda kalmışsa track.nc'den üret
        import xarray as xr
        ds = xr.open_dataset(out / "track.nc"); ep = agg.endpoints_from_result(ds); ds.close()
    rows, zone, zn = agg.aggregate(out, origins, ep, meta)
    coast = a.coast or (RUNS / "schism" / str(meta.get("run", "izmir")) / "opendrift" / "schism_surface.nc")
    try: agg.plot_matrix(out, origins, ep, rows, zn, meta, coast_file=coast)
    except Exception as e:  # noqa: BLE001
        print("[43] çizim atlandı:", e)
    print("[43] yenilendi:", out)

if __name__ == "__main__":
    main()
