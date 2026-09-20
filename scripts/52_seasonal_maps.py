"""Yıllık OpenDrift partilerini (51) mevsim/yıl bazında birleştir: kaynak→kıyı matrisleri, hücre haritaları, kıyı yükü,
web sitesi GeoJSON/JSON'ları.

Girdi : runs/opendrift/year/<mode>_<YYYY-MM>[_tag]/{endpoints.csv, origins.csv, meta.json}
Çıktı : runs/opendrift/year/summary[_tag]/
          sources_matrix_<dönem>.csv     kaynak × bölge payı (dönem: yil, SON, DJF, MAM, JJA, aylar)
          grid_dominant_<dönem>.png      hücre → baskın varış bölgesi haritası
          coast_load_<dönem>.csv         bölge başına varış payı (tüm ızgara hücreleri eşit ağırlıklı)
          web/cells.geojson              hücre başına {dönem: {zone: pay}} + t_med, strand (web sitesi girdisi)
          web/sources.json               kaynak başına aynı yapı
          web/zones.json                 bölge adları/kutuları
Kullanım: python scripts/52_seasonal_maps.py [--tag w1]
"""
from __future__ import annotations
import argparse, csv, json
from collections import defaultdict
from pathlib import Path
import numpy as np

from common import RUNS, CFG, bbox
import od_agg as agg

SEASONS = {"DJF": (12, 1, 2), "MAM": (3, 4, 5), "JJA": (6, 7, 8), "SON": (9, 10, 11)}
COSLAT = np.cos(np.deg2rad(38.5))

def log(*a): print("[52]", *a, flush=True)

def load(mode, tag):
    base = RUNS / "opendrift" / "year"
    dirs = sorted(d for d in base.glob(f"{mode}_????-??{('_' + tag) if tag else ''}") if (d / "endpoints.csv").exists())
    months = {}
    for d in dirs:
        ym = d.name.split("_")[1]
        origins = list(csv.DictReader(open(d / "origins.csv", encoding="utf-8")))
        ep = agg.endpoints_from_csv(d / "endpoints.csv", origins)
        months[ym] = (origins, ep)
    return months

def period_of(ym):
    m = int(ym[5:7]); return next(s for s, ms in SEASONS.items() if m in ms)

def combine(months, keys):
    """Seçili ayları birleştir: origin id → (n, zone sayaçları, süreler)."""
    acc = defaultdict(lambda: {"n": 0, "z": defaultdict(int), "t": []})
    ref = None
    for ym in keys:
        if ym not in months: continue
        origins, ep = months[ym]; ref = origins
        zone, Z = agg.assign_zones(ep["lon"], ep["lat"], ep["stranded"])
        dt = ep["t_end"] - ep["t_rel"]
        for i in range(len(zone)):
            if zone[i] == "NA": continue
            o = origins[ep["origin_idx"][i]]["origin"]; a = acc[o]; a["n"] += 1; a["z"][zone[i]] += 1
            if ep["stranded"][i]: a["t"].append(float(dt[i]))
    return acc, ref

def rows_from(acc, origins, zids):
    rows = []
    for og in origins:
        a = acc.get(og["origin"])
        if not a or a["n"] == 0: continue
        r = {"origin": og["origin"], "name": og["name"], "lon": f"{float(og['lon']):.4f}", "lat": f"{float(og['lat']):.4f}", "n": a["n"],
             "stranded_frac": f"{1 - a['z'].get('Z12', 0) / a['n']:.3f}", "t_strand_med_h": f"{np.median(a['t']):.1f}" if a["t"] else ""}
        for z in zids: r[z] = f"{a['z'].get(z, 0) / a['n']:.3f}"
        dom = max([z for z in zids if z != "Z12"] + ["Z12"], key=lambda z: float(r[z])); r["dominant"] = dom; r["dominant_frac"] = r[dom]
        rows.append(r)
    return rows

def plot_dominant(out, rows, zn, title, cell_km, coast_file):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    x0, x1, y0, y1 = bbox("B_model")
    fig, ax = plt.subplots(figsize=(11, 8))
    if coast_file and Path(coast_file).exists(): ax.add_collection(LineCollection(agg.mesh_coast(Path(coast_file)), colors="0.35", linewidths=0.5, zorder=1))
    zl = sorted(set(r["dominant"] for r in rows)); cm = plt.get_cmap("tab20", max(len(zl), 1))
    for j, z in enumerate(zl):
        rr = [r for r in rows if r["dominant"] == z]
        ax.scatter([float(r["lon"]) for r in rr], [float(r["lat"]) for r in rr], s=(cell_km * 9) ** 2, marker="s", color=cm(j), label=f"{z} {zn.get(z, '')}")
    ax.legend(fontsize=7, loc="upper left"); ax.set_title(title); ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect(1 / COSLAT); ax.grid(alpha=0.3)
    fig.savefig(out, dpi=120, bbox_inches="tight"); plt.close(fig)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default=""); ap.add_argument("--coast", default=None)
    a = ap.parse_args()
    out = RUNS / "opendrift" / "year" / f"summary{('_' + a.tag) if a.tag else ''}"; (out / "web").mkdir(parents=True, exist_ok=True)
    Z = agg.zones(); zn = agg.zone_names(Z); zids = [z[0] for z in Z if z[0] != "Z12"] + ["Z00", "Z12"]
    coast = a.coast or next(iter(sorted((RUNS.parent / "data" / "processed").glob("schism_surface_*.nc"))), None)
    json.dump({"zones": [{"id": z[0], "name": z[1], "bbox": z[2:]} for z in Z] + [{"id": "Z00", "name": agg.Z00[1], "bbox": [None] * 4}]},
              open(out / "web" / "zones.json", "w", encoding="utf-8"), ensure_ascii=False)
    web = {}
    for mode in ("sources", "grid"):
        months = load(mode, a.tag)
        if not months: log(mode, "için aylık parti yok"); continue
        keys = sorted(months); log(f"{mode}: {len(keys)} ay ({keys[0]}..{keys[-1]})")
        periods = {"yil": keys}
        for s in SEASONS:
            ks = [k for k in keys if period_of(k) == s]
            if ks: periods[s] = ks
        for k in keys: periods[k] = [k]
        per_origin = defaultdict(dict)
        cell_km = 1.0
        try: cell_km = float(json.load(open(RUNS / "opendrift" / "year" / f"{mode}_{keys[0]}{('_' + a.tag) if a.tag else ''}" / "meta.json")).get("cell_km", 1.0))
        except Exception: pass
        for pname, ks in periods.items():
            acc, origins = combine(months, ks)
            rows = rows_from(acc, origins, zids)
            if not rows: continue
            with open(out / f"{mode}_matrix_{pname}.csv", "w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
            if mode == "grid":
                load_rows = [{"zone_id": z, "zone": zn.get(z, ""), "share": f"{np.mean([float(r[z]) for r in rows]):.4f}"} for z in zids]
                with open(out / f"coast_load_{pname}.csv", "w", encoding="utf-8", newline="") as fh:
                    w = csv.DictWriter(fh, fieldnames=["zone_id", "zone", "share"]); w.writeheader(); w.writerows(load_rows)
                if pname in ("yil",) or pname in SEASONS:
                    plot_dominant(out / f"grid_dominant_{pname}.png", rows, zn, f"hücre → baskın varış bölgesi — {pname} ({len(ks)} ay)", cell_km, coast)
            for r in rows:
                per_origin[r["origin"]][pname] = {"n": r["n"], "strand": round(float(r["stranded_frac"]), 3),
                                                  "t_med_h": float(r["t_strand_med_h"]) if r["t_strand_med_h"] else None,
                                                  "zones": {z: round(float(r[z]), 3) for z in zids if float(r[z]) >= 0.005}}
        _, origins = combine(months, keys)
        feats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(float(og["lon"]), 5), round(float(og["lat"]), 5)]},
                  "properties": {"id": og["origin"], "name": og["name"], "periods": per_origin.get(og["origin"], {})}} for og in origins if og["origin"] in per_origin]
        doc = {"type": "FeatureCollection", "mode": mode, "cell_km": cell_km if mode == "grid" else None, "months": keys,
               "periods": list(periods.keys()), "features": feats}
        fn = "cells.geojson" if mode == "grid" else "sources.json"
        json.dump(doc, open(out / "web" / fn, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        web[mode] = len(feats)
        # kısa özet
        acc, origins = combine(months, keys); rows = rows_from(acc, origins, zids)
        tot = {z: float(np.mean([float(r[z]) for r in rows])) for z in zids}
        log(f"{mode} yıl: bölge payları " + ", ".join(f"{z} %{100*tot[z]:.0f}" for z in zids if tot[z] >= 0.005))
    log("çıktılar:", out, "| web:", web)

if __name__ == "__main__":
    main()
