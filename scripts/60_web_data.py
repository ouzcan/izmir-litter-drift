"""Web sitesi veri paketi: OpenDrift koşularından (42 haftalık / 51 yıllık) hücre ve kaynak dosyaları → web/data/.

Her dönem için bir koşu klasörü (endpoints.csv + origins.csv gerekir):
    python scripts/60_web_data.py --period hafta_2026-09=runs/opendrift/matrix_izmir3d_grid_20260906 \\
        --sources hafta_2026-09=runs/opendrift/matrix_izmir3d_sources_20260906 --label hafta_2026-09="6–13 Eylül 2026 (K–KD rüzgârı)"
Yıllık akış bittiğinde 51'in aylık klasörleri mevsimlere toplanır:
    python scripts/60_web_data.py --year            # runs/opendrift/year/grid_*, sources_* → yil, DJF, MAM, JJA, SON
Çıktı (web/data/): cells_<dönem>.json — DÖNEM BAŞINA ayrı dosya (site açılışta yalnız seçili dönemi indirir;
       tek parça hâlinde 17 dönem 12 MB tutuyordu). Her hücre: {id, lon, lat, r: {p: {bölge: pay}, t: medyan saat,
       s: kıyıya vurma oranı, n, e: [[lon, lat, saat], …] örnek varış noktaları, x: [[lon, lat, saat], …] örnek
       ALAN DIŞINA ÇIKIŞ noktaları (status outside; site s olasılığıyla e'den, 1-s ile x'ten seçer)}}.
       Ayrıca sources.json (tüm dönemler tek dosyada, küçük), zones.json (model alanı dışı bölgeler "outside": true
       ile işaretli), meta.json (dönem listesi + cells_files eşlemesi).
"""
from __future__ import annotations
import argparse, csv, glob, json, random
from collections import defaultdict
from pathlib import Path
import numpy as np

from common import ROOT, RUNS, CFG, bbox
import od_agg as agg

WEB = ROOT / "web" / "data"
SEASONS = {"DJF": (12, 1, 2), "MAM": (3, 4, 5), "JJA": (6, 7, 8), "SON": (9, 10, 11)}
N_END = 8   # hücre/dönem başına saklanan örnek varış noktası

def log(*a): print("[60]", *a, flush=True)

def read_run(d: Path):
    origins = list(csv.DictReader(open(d / "origins.csv", encoding="utf-8")))
    ep = agg.endpoints_from_csv(d / "endpoints.csv", origins)
    return origins, ep

def accumulate(acc, origins, ep, rnd):
    zone, Z = agg.assign_zones(ep["lon"], ep["lat"], ep["stranded"])
    dt = ep["t_end"] - ep["t_rel"]
    for i in range(len(zone)):
        if zone[i] == "NA": continue
        o = origins[ep["origin_idx"][i]]; a = acc[o["origin"]]
        a["name"] = o["name"]; a["lon"] = float(o["lon"]); a["lat"] = float(o["lat"])
        a["n"] += 1; a["z"][zone[i]] += 1
        if ep["stranded"][i]:
            a["ns"] += 1; a["t"].append(float(dt[i]))
            # rezervuar örnekleme: N_END varış noktası
            k = a["k"]; a["k"] += 1
            pt = [round(float(ep["lon"][i]), 4), round(float(ep["lat"][i]), 4), round(float(dt[i]), 1)]
            if len(a["e"]) < N_END: a["e"].append(pt)
            else:
                j = rnd.randint(0, k)
                if j < N_END: a["e"][j] = pt
        elif ep.get("status") is not None and ep["status"][i] == "outside":
            k = a["kx"]; a["kx"] += 1
            pt = [round(float(ep["lon"][i]), 4), round(float(ep["lat"][i]), 4), round(float(dt[i]), 1)]
            if len(a["x"]) < N_END: a["x"].append(pt)
            else:
                j = rnd.randint(0, k)
                if j < N_END: a["x"][j] = pt

def finish(acc):
    out = {}
    for oid, a in acc.items():
        if a["n"] == 0: continue
        p = {z: round(c / a["n"], 3) for z, c in a["z"].items() if c / a["n"] >= 0.005}
        out[oid] = {"p": p, "t": round(float(np.median(a["t"])), 1) if a["t"] else None,
                    "s": round(a["ns"] / a["n"], 3), "n": a["n"], "e": a["e"], "x": a["x"]}
    return out

def new_acc():
    return defaultdict(lambda: {"n": 0, "ns": 0, "z": defaultdict(int), "t": [], "e": [], "k": 0, "x": [], "kx": 0, "name": "", "lon": 0.0, "lat": 0.0})

def build(period_runs: dict, labels: dict, mode: str, rnd):
    """period_runs: {dönem: [klasörler]} → (özellikler, dönem sırası)"""
    feats = {}; order = []
    for per, dirs in period_runs.items():
        acc = new_acc()
        for d in dirs:
            origins, ep = read_run(Path(d)); accumulate(acc, origins, ep, rnd)
        res = finish(acc)
        if not res: continue
        order.append(per)
        for oid, r in res.items():
            f = feats.setdefault(oid, {"id": oid, "lon": round(acc[oid]["lon"], 5), "lat": round(acc[oid]["lat"], 5), "d": {}})
            if mode == "sources": f["name"] = acc[oid]["name"]
            f["d"][per] = r
        log(f"{mode} {per}: {len(res)} nokta, {sum(a['n'] for a in acc.values())} parçacık")
    return list(feats.values()), order

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", action="append", default=[], help="dönem=ızgara koşu klasörü (tekrarlanabilir)")
    ap.add_argument("--sources", action="append", default=[], help="dönem=kaynak koşu klasörü")
    ap.add_argument("--label", action="append", default=[], help="dönem=etiket")
    ap.add_argument("--year", action="store_true", help="runs/opendrift/year altındaki aylık partileri mevsim/yıl olarak topla")
    ap.add_argument("--tag", default="")
    a = ap.parse_args(); rnd = random.Random(42)
    WEB.mkdir(parents=True, exist_ok=True)
    grid = defaultdict(list); src = defaultdict(list)
    labels = {"yil": "Yıl (Eyl 2025 – Ağu 2026)", "DJF": "Kış (Ara–Şub)", "MAM": "İlkbahar (Mar–May)", "JJA": "Yaz (Haz–Ağu)", "SON": "Sonbahar (Eyl–Kas)"}
    for kv in a.period: k, v = kv.split("=", 1); grid[k].append(v)
    for kv in a.sources: k, v = kv.split("=", 1); src[k].append(v)
    for kv in a.label: k, v = kv.split("=", 1); labels[k] = v
    if a.year:
        base = RUNS / "opendrift" / "year"
        for mode, store in (("grid", grid), ("sources", src)):
            for d in sorted(base.glob(f"{mode}_????-??{('_' + a.tag) if a.tag else ''}")):
                if not (d / "endpoints.csv").exists(): continue
                ym = d.name.split("_")[1]; m = int(ym[5:7]); season = next(s for s, ms in SEASONS.items() if m in ms)
                store["yil"].append(str(d)); store[season].append(str(d)); store[ym].append(str(d)); labels.setdefault(ym, ym)
    cells, order_c = build(grid, labels, "grid", rnd)
    sources, order_s = build(src, labels, "sources", rnd)
    Z = agg.zones(); zn = agg.zone_names(Z)
    x0, x1, y0, y1 = bbox("B_model")
    periods = [p for p in dict.fromkeys(order_c + order_s)]
    meta = {"periods": [{"id": p, "label": labels.get(p, p)} for p in periods], "default_period": periods[0] if periods else None,
            "domain": [x0, y0, x1, y1], "cell_km": 1.0, "n_cells": len(cells), "n_sources": len(sources),
            "generated": __import__("datetime").date.today().isoformat(),
            "model": "SCHISM 3B (11 sigma, ~110 m iç körfez) + OpenDrift; rüzgâr ERA5, windage %2, difüzyon 5 m²/s; Stokes yok"}
    # Hücreler DÖNEM BAŞINA ayrı dosyada: site açılışta yalnız seçili dönemi indirir.
    # (Tek parça cells.json 17 dönemde 12 MB'a çıkıyordu ve harita görünmeden önce tamamı iniyordu.)
    for f in WEB.glob("cells_*.json"): f.unlink()
    if (WEB / "cells.json").exists(): (WEB / "cells.json").unlink()   # eski tek parça dosya
    sizes = []
    for per in order_c:
        fc = [{"id": c["id"], "lon": c["lon"], "lat": c["lat"], "r": c["d"][per]} for c in cells if per in c["d"]]
        fp = WEB / f"cells_{per}.json"
        json.dump({"type": "cells", "period": per, "features": fc}, open(fp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        sizes.append(fp.stat().st_size)
    json.dump({"type": "sources", "features": sources}, open(WEB / "sources.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    # Model alanının dışında kalan kıyı bölgeleri işaretlenir: bu bölgeler yapısal olarak sıfır alır,
    # sitede "veri yok" değil "model alanı dışı" diye gösterilmeli.
    def inside_frac(z):
        _, _, zx0, zx1, zy0, zy1 = z
        if zx0 is None: return 0.0                       # Z12: kutusuz, zaten "alan dışı" kovası
        ox, oy = max(0.0, min(zx1, x1) - max(zx0, x0)), max(0.0, min(zy1, y1) - max(zy0, y0))
        area = (zx1 - zx0) * (zy1 - zy0)
        return (ox * oy) / area if area > 0 else 0.0
    zlist = []
    for z in Z:
        out = z[0] != "Z12" and inside_frac(z) < 0.2     # kutusunun %20'sinden azı alan içindeyse
        zlist.append({"id": z[0], "name": z[1], "bbox": list(z[2:]), **({"outside": True} if out else {})})
    zlist.append({"id": "Z00", "name": agg.Z00[1], "bbox": [None] * 4})
    json.dump({"zones": zlist}, open(WEB / "zones.json", "w", encoding="utf-8"), ensure_ascii=False)
    disi = [z["id"] for z in zlist if z.get("outside")]
    if disi: log("model alanı dışı bölgeler (sitede öyle etiketlenecek):", ", ".join(disi))
    meta["cells_files"] = {p: f"cells_{p}.json" for p in order_c}
    json.dump(meta, open(WEB / "meta.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"web/data yazıldı: {len(cells)} hücre, {len(sources)} kaynak, {len(order_c)} dönem dosyası; "
        f"dönem başına {min(sizes)/1e3:.0f}–{max(sizes)/1e3:.0f} KB, toplam {sum(sizes)/1e6:.1f} MB")

if __name__ == "__main__":
    main()
