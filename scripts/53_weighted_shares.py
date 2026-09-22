"""Kaynak ağırlıklandırılmış kıyı bölgesi payları — koşu tekrarı GEREKTİRMEZ.

Sorun: `od_agg.py` bölge paylarını salım noktalarının DÜZ ORTALAMASI olarak veriyor, yani 23 kaynağın
hepsi eşit çöp yükü taşıyormuş gibi. "Z04 %33" gibi bir rakam o yüzden İzmir hakkında değil,
`sources.csv`'nin şekli hakkında bir cümle oluyor.

Çözüm: `sources_matrix_<dönem>.csv` zaten kaynak başına bölge paylarını tutuyor → ağırlıklı ortalama
saf post-processing. Tek bir "doğru" ağırlıklandırma olmadığı için üç senaryo koşulur ve yayılım raporlanır
(bkz. config/source_weights.csv).

Kullanım:
    python scripts/53_weighted_shares.py                 # tüm dönemler
    python scripts/53_weighted_shares.py --period yil    # tek dönem
Çıktı: runs/opendrift/year/summary/weighted_shares.csv (dönem x senaryo x bölge)
       runs/opendrift/year/summary/weighted_shares.txt  (okunur karşılaştırma tablosu)
"""
from __future__ import annotations
import argparse, csv
from pathlib import Path

from common import ROOT, RUNS, CFG
import od_agg as agg

SUM = RUNS / "opendrift" / "year" / "summary"
# Grup payları — config/source_weights.csv başlığında gerekçesi var
GRUP_PAYI = {"dere": 0.69, "iskele": 0.12, "marina": 0.03, "liman": 0.14, "barinak": 0.02}
SENARYOLAR = ["esit", "havza", "kentsel"]

def log(*a): print("[53]", *a, flush=True)

def read_weights():
    rows = []
    with open(CFG / "source_weights.csv", encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip(): continue
            rows.append(line)
    r = list(csv.DictReader(rows))
    def f(v, d=0.0):
        try: return float(v)
        except (TypeError, ValueError): return d
    out = {}
    for w in r:
        out[w["id"]] = {"grup": w["grup"], "havza": f(w["havza_km2"]), "kentsel": f(w["kentsel_pay"], 1.0),
                        "faaliyet": f(w["faaliyet"]), "guven": w["guven"]}
    return out

def scenario_weights(W, ids, senaryo):
    """id -> ağırlık (toplamı 1). Grup payı sabit; grup içi dağılım senaryoya göre."""
    if senaryo == "esit":
        return {i: 1.0 / len(ids) for i in ids}
    ham = {}
    for i in ids:
        w = W[i]
        if w["grup"] == "dere":
            ham[i] = w["havza"] * (w["kentsel"] if senaryo == "kentsel" else 1.0)
        else:
            ham[i] = w["faaliyet"]
    out = {}
    for g, pay in GRUP_PAYI.items():
        gid = [i for i in ids if W[i]["grup"] == g]
        tot = sum(ham[i] for i in gid)
        for i in gid: out[i] = pay * (ham[i] / tot if tot > 0 else 1.0 / len(gid))
    s = sum(out.values())
    return {i: v / s for i, v in out.items()}      # koşuya girmeyen grup varsa yeniden normalize

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", default=None)
    a = ap.parse_args()
    W = read_weights()
    zn = agg.zone_names(agg.zones())
    files = sorted(SUM.glob("sources_matrix_*.csv"))
    if a.period: files = [f for f in files if f.stem.endswith(a.period)]
    if not files: raise SystemExit(f"{SUM}/sources_matrix_*.csv yok — önce 52_seasonal_maps.py")

    satirlar, metin = [], []
    for f in files:
        per = f.stem.replace("sources_matrix_", "")
        rows = list(csv.DictReader(open(f, encoding="utf-8")))
        zids = [k for k in rows[0] if k.startswith("Z")]
        ids = [r["origin"] for r in rows]
        eksik = [i for i in ids if i not in W]
        if eksik: raise SystemExit(f"{per}: source_weights.csv'de yok: {', '.join(eksik)}")
        paylar = {}
        for sen in SENARYOLAR:
            w = scenario_weights(W, ids, sen)
            paylar[sen] = {z: sum(w[r["origin"]] * float(r[z]) for r in rows) for z in zids}
            for z in zids:
                satirlar.append({"donem": per, "senaryo": sen, "zone_id": z, "zone": zn.get(z, z),
                                 "pay": f"{paylar[sen][z]:.4f}"})
        if per in ("yil", "DJF", "MAM", "JJA", "SON"):
            metin.append(f"\n=== {per} — kaynak ağırlıklandırmasına göre kıyı bölgesi payları ===")
            metin.append(f"{'bölge':38s} {'eşit':>7s} {'havza':>7s} {'kentsel':>8s}   fark")
            onemli = sorted(zids, key=lambda z: -max(paylar[s][z] for s in SENARYOLAR))
            for z in onemli:
                v = [paylar[s][z] for s in SENARYOLAR]
                if max(v) < 0.01: continue
                metin.append(f"{(z + ' ' + zn.get(z, ''))[:38]:38s} {100*v[0]:6.1f}% {100*v[1]:6.1f}% {100*v[2]:7.1f}%   "
                             f"{100*(max(v)-min(v)):4.1f} puan")
    with open(SUM / "weighted_shares.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["donem", "senaryo", "zone_id", "zone", "pay"]); w.writeheader(); w.writerows(satirlar)

    W_ids = [r["origin"] for r in csv.DictReader(open(files[0], encoding="utf-8"))]
    bas = ["Senaryo ağırlıkları (kaynak başına, toplam %100):", f"{'kaynak':6s} {'grup':8s} {'eşit':>7s} {'havza':>7s} {'kentsel':>8s}  güven"]
    ws = {s: scenario_weights(W, W_ids, s) for s in SENARYOLAR}
    for i in W_ids:
        bas.append(f"{i:6s} {W[i]['grup']:8s} {100*ws['esit'][i]:6.1f}% {100*ws['havza'][i]:6.1f}% {100*ws['kentsel'][i]:7.1f}%  {W[i]['guven']}")
    txt = "\n".join(bas + metin)
    (SUM / "weighted_shares.txt").write_text(txt, encoding="utf-8")
    print(txt)
    log("çıktılar:", SUM / "weighted_shares.csv", "+ .txt")

if __name__ == "__main__":
    main()
