"""Duyarlılık varyantlarını tek tabloda karşılaştır — ölçütler koşudan önce sabit, seçme yok.

Girdi : runs/opendrift/year/<mode>_<YYYY-MM>_<tag>/{endpoints.csv, origins.csv, meta.json} (51 çıktıları)
Çıktı : runs/opendrift/year/sensitivity/
          sensitivity_<mode>.csv   varyant × ölçüt (bölge payları %, vuran %, alan dışı %, denizde %, medyan vurma süresi, ilk-3)
          sensitivity_<mode>.md    makale için: bölge × varyant tablosu + tabana göre fark (puan) + sıralama değişti mi
Ölçütler (yıl = eldeki tüm aylar birleşik; salım noktaları eşit ağırlıklı — 52 ile aynı hesap):
  - bölge payları (Z01..Z16 + Z12), kıyıya vuran %, alan dışına çıkan % ('outside'), izleme sonunda denizde % ('active'),
    medyan vurma süresi (saat; refloat varyantında ilk temas), ilk-3 bölge ve sırası
  - tabana göre fark: puan (yüzde noktası); "sıralama": ilk-3 küme ve sıra aynı mı
Varyantların ay kümesi tabandan farklıysa uyarır ve yalnız ORTAK ayları karşılaştırır.

Kullanım (Windows, litter):
    python scripts/54_sensitivity.py                          # taban: base2 varsa o, yoksa etiketsiz; varyant: bulunan tüm etiketler
    python scripts/54_sensitivity.py --base base2 --tags w3 w1 w0 d1 d10 rf5
"""
from __future__ import annotations
import argparse, csv, importlib, json
from pathlib import Path
import numpy as np

from common import RUNS
import od_agg as agg
m52 = importlib.import_module("52_seasonal_maps")

YEAR = RUNS / "opendrift" / "year"

def log(*a): print("[54]", *a, flush=True)

def tags_present(mode):
    out = set()
    for d in YEAR.glob(f"{mode}_????-??*"):
        if not (d / "endpoints.csv").exists(): continue
        parts = d.name.split("_", 2); out.add(parts[2] if len(parts) == 3 else "")
    return out

def label_of(mode, tag, months):
    try: m = json.load(open(YEAR / f"{mode}_{months[0]}{('_' + tag) if tag else ''}" / "meta.json", encoding="utf-8"))
    except Exception: return tag or "taban"
    bits = []
    if not m.get("wind", True): bits.append("rüzgâr yok")
    else: bits.append(f"windage {m.get('windage', 0.02):g}")
    if float(m.get("diffusivity", 5)) != 5: bits.append(f"difüzyon {m.get('diffusivity'):g}")
    bits.append("alan dışı biter" if m.get("deactivate_outside") else "alan dışı sürükleniyor")
    if m.get("refloat_days"): bits.append(f"yeniden yüzdürme λ_R {m['refloat_days']:g} g")
    if mode == "grid" and float(m.get("cell_km", 1)) != 1: bits.append(f"ızgara {float(m['cell_km']):g} km")
    return ", ".join(bits)

def metrics(mode, tag, keys, zids):
    months = m52.load(mode, tag)
    have = [k for k in keys if k in months]
    acc, origins = m52.combine(months, have)
    rows = m52.rows_from(acc, origins, zids)
    share = {z: 100 * float(np.mean([float(r[z]) for r in rows])) for z in zids}
    st = np.concatenate([np.asarray(months[k][1]["status"], dtype=object) for k in have])
    stranded = np.concatenate([months[k][1]["stranded"] for k in have])
    dt = np.concatenate([(months[k][1]["t_end"] - months[k][1]["t_rel"]) for k in have])
    fin = st != "NA"
    top = sorted([z for z in zids if z != "Z12"], key=lambda z: -share[z])[:3]
    return {"tag": tag or "", "months": have, "n_origins": len(rows), "n_particles": int(fin.sum()),
            "strand_pct": 100 * float(stranded[fin].mean()), "outside_pct": 100 * float(np.mean(st[fin] == "outside")),
            "afloat_pct": 100 * float(np.mean(st[fin] == "active")),
            "t_med_h": float(np.median(dt[stranded])) if stranded.any() else float("nan"),
            "top3": top, "share": share}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--base", default=None); ap.add_argument("--tags", nargs="*", default=None)
    ap.add_argument("--modes", nargs="*", default=["grid", "sources"])
    a = ap.parse_args()
    out = YEAR / "sensitivity"; out.mkdir(parents=True, exist_ok=True)
    Z = agg.zones(); zn = agg.zone_names(Z); zids = [z[0] for z in Z if z[0] != "Z12"] + ["Z00", "Z12"]
    for mode in a.modes:
        present = tags_present(mode)
        if not present: log(mode, "için koşu yok"); continue
        base = a.base if a.base is not None else ("base2" if "base2" in present else "")
        if base not in present: log(mode, f"taban '{base}' yok; mevcut: {sorted(present)}"); continue
        tags = [t for t in (a.tags if a.tags is not None else sorted(present)) if t != base and t in present]
        keys = sorted(m52.load(mode, base))
        for t in tags:
            kt = set(m52.load(mode, t)); miss = [k for k in keys if k not in kt]
            if miss: log(f"uyarı: {mode} '{t}' eksik aylar {miss} → ortak aylarla karşılaştırılıyor")
            keys = [k for k in keys if k in kt]
        if not keys: log(mode, "ortak ay yok"); continue
        log(f"{mode}: taban '{base or 'etiketsiz'}', varyantlar {tags}, ortak aylar {keys[0]}..{keys[-1]} ({len(keys)})")
        M = [metrics(mode, base, keys, zids)] + [metrics(mode, t, keys, zids) for t in tags]
        for m in M: m["label"] = label_of(mode, m["tag"], keys)
        B = M[0]
        # CSV: varyant × ölçüt
        cols = ["tag", "label", "n_months", "n_origins", "n_particles", "strand_pct", "outside_pct", "afloat_pct", "t_med_h",
                "top1", "top2", "top3", "top3_same_set", "top3_same_order", "max_abs_delta_pt", "max_abs_delta_zone"] + zids
        with open(out / f"sensitivity_{mode}.csv", "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols); w.writeheader()
            for m in M:
                d = {z: m["share"][z] - B["share"][z] for z in zids}; zmax = max(zids, key=lambda z: abs(d[z]))
                w.writerow({"tag": m["tag"] or "taban", "label": m["label"], "n_months": len(m["months"]), "n_origins": m["n_origins"], "n_particles": m["n_particles"],
                            "strand_pct": f"{m['strand_pct']:.1f}", "outside_pct": f"{m['outside_pct']:.1f}", "afloat_pct": f"{m['afloat_pct']:.1f}",
                            "t_med_h": f"{m['t_med_h']:.1f}", "top1": m["top3"][0], "top2": m["top3"][1], "top3": m["top3"][2],
                            "top3_same_set": int(set(m["top3"]) == set(B["top3"])), "top3_same_order": int(m["top3"] == B["top3"]),
                            "max_abs_delta_pt": f"{abs(d[zmax]):.1f}", "max_abs_delta_zone": zmax, **{z: f"{m['share'][z]:.1f}" for z in zids}})
        # Markdown: bölge × varyant (taban mutlak %, varyantlar % ve parantezde tabana göre puan)
        L = [f"# Duyarlılık — {mode} ({len(keys)} ay: {keys[0]}..{keys[-1]}; salım noktaları eşit ağırlıklı)", "",
             "| | " + " | ".join(f"**{m['tag'] or 'taban'}**<br>{m['label']}" for m in M) + " |", "|---|" + "---|" * len(M)]
        def cell(m, z):
            v = m["share"][z]
            if m is B: return f"{v:.1f}"
            return f"{v:.1f} ({m['share'][z] - B['share'][z]:+.1f})"
        for z in zids:
            if max(m["share"][z] for m in M) < 0.5: continue
            L.append(f"| {z} {zn.get(z, '')} | " + " | ".join(cell(m, z) for m in M) + " |")
        L.append("| kıyıya vuran % | " + " | ".join(f"{m['strand_pct']:.1f}" for m in M) + " |")
        L.append("| alan dışına çıkan % | " + " | ".join(f"{m['outside_pct']:.1f}" for m in M) + " |")
        L.append("| izleme sonunda denizde % | " + " | ".join(f"{m['afloat_pct']:.1f}" for m in M) + " |")
        L.append("| medyan vurma süresi (sa) | " + " | ".join(f"{m['t_med_h']:.0f}" for m in M) + " |")
        L.append("| ilk 3 bölge | " + " | ".join(" › ".join(m["top3"]) + ("" if m is B else (" ✓" if m["top3"] == B["top3"] else (" (sıra)" if set(m["top3"]) == set(B["top3"]) else " **(küme)**"))) for m in M) + " |")
        L += ["", "Parantez: tabana göre fark, yüzde puanı. ✓ ilk-3 aynı sırayla; (sıra) aynı küme farklı sıra; (küme) farklı bölge girdi.",
              "Z12 = alan dışına çıkan + izleme sonunda denizde kalan. Refloat varyantında vurma süresi = ilk kıyı teması."]
        (out / f"sensitivity_{mode}.md").write_text("\n".join(L), encoding="utf-8")
        print("\n".join(L)); print()
    log("çıktılar:", out)

if __name__ == "__main__":
    main()
