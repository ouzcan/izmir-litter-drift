"""Doğrulama Katman 1a — su seviyesi: SCHISM ↔ Menteş mareografı (IOC Sea Level Monitoring).

İstasyon: Menteş (kod `ment`), 38,4277°K 26,7166°D — TUDES/Harita Genel Müdürlüğü, radar sensör, 30 sn.
Model alanının içinde; en yakın ağ düğümü ~44 m uzakta. Ücretsiz, kayıt gerekmiyor.

İki aşama (indirme ayrı, çünkü IOC bazı ağlardan engelli):
    python scripts/70_validate_sealevel.py --download          # gün gün indirir, data/raw/obs altına, atlanabilir
    python scripts/70_validate_sealevel.py                     # karşılaştırma + özet + grafik

Çıktı: data/processed/obs_sealevel_ment.csv (saatlik ortalama),
       docs/sonuclar/dogrulama/sealevel_summary.txt, sealevel_series.png, sealevel_scatter.png

Metrikler: bias, RMSE, merkezlenmiş RMSE, Pearson r, std oranı. Datum farklı olduğu için ORTALAMALAR ÇIKARILIR
(model datumu başlangıç seviyesi, mareograf kendi sıfırına göre) — karşılaştırılan şey salınım, mutlak seviye değil.
`utide` kuruluysa M2/S2/K1/O1 genlik-faz karşılaştırması da yapılır (pip install utide).
"""
from __future__ import annotations
import argparse, csv, json, sys, time
from datetime import date, datetime, timedelta
from pathlib import Path
import numpy as np

from common import ROOT, RAW, PROC, params

OBS = RAW / "obs"
OUT = ROOT / "docs" / "sonuclar" / "dogrulama"
CODE = "ment"
LON, LAT = 26.7166, 38.4277
API = "https://www.ioc-sealevelmonitoring.org/service.php"

def log(*a): print("[70]", *a, flush=True)

# ---------- indirme
def download(d0: date, d1: date, force=False):
    import urllib.request, urllib.error
    OBS.mkdir(parents=True, exist_ok=True)
    d, n_new, n_skip, n_err = d0, 0, 0, 0
    while d < d1:
        f = OBS / f"ioc_{CODE}_{d:%Y-%m-%d}.json"
        if f.exists() and not force: n_skip += 1; d += timedelta(days=1); continue
        url = (f"{API}?query=data&code={CODE}&timestart={d:%Y-%m-%d}T00:00:00"
               f"&timestop={d + timedelta(days=1):%Y-%m-%d}T00:00:00&format=json")
        try:
            with urllib.request.urlopen(url, timeout=60) as r: raw = r.read().decode("utf-8", "replace")
            json.loads(raw)                      # biçim denetimi
            f.write_text(raw, encoding="utf-8"); n_new += 1
        except Exception as e:
            n_err += 1; log(f"{d:%Y-%m-%d}: {type(e).__name__} {e}")
            if n_err > 10: raise SystemExit("[70] 10'dan fazla hata — ağ ya da API sorunu, durduruldu")
        time.sleep(0.4)
        if n_new % 30 == 0 and n_new: log(f"  {d:%Y-%m-%d} … {n_new} gün indi")
        d += timedelta(days=1)
    log(f"indirme bitti: {n_new} yeni, {n_skip} atlandı, {n_err} hata → {OBS}")

def build_obs_csv():
    """Günlük JSON'ları saatlik ortalama tek CSV'ye toplar. Sensör: en çok kaydı olan."""
    per_hour, sensors = {}, {}
    for f in sorted(OBS.glob(f"ioc_{CODE}_*.json")):
        try: rows = json.loads(f.read_text(encoding="utf-8"))
        except Exception: continue
        if not isinstance(rows, list): continue
        for r in rows:
            s = r.get("sensor", "?"); sensors[s] = sensors.get(s, 0) + 1
    if not sensors: raise SystemExit("[70] indirilmiş veri yok — önce --download")
    sensor = max(sensors, key=sensors.get)
    log("sensörler:", ", ".join(f"{k}={v}" for k, v in sorted(sensors.items(), key=lambda kv: -kv[1])), f"→ seçilen: {sensor}")
    for f in sorted(OBS.glob(f"ioc_{CODE}_*.json")):
        try: rows = json.loads(f.read_text(encoding="utf-8"))
        except Exception: continue
        if not isinstance(rows, list): continue
        for r in rows:
            if r.get("sensor") != sensor: continue
            try:
                t = datetime.strptime(r["stime"][:19], "%Y-%m-%d %H:%M:%S").replace(minute=0, second=0)
                v = float(r["slevel"])
            except (KeyError, ValueError, TypeError): continue
            if not np.isfinite(v): continue
            per_hour.setdefault(t, []).append(v)
    PROC.mkdir(parents=True, exist_ok=True)
    out = PROC / f"obs_sealevel_{CODE}.csv"
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh); w.writerow(["time", "slevel_m", "n"])
        for t in sorted(per_hour):
            v = per_hour[t]
            w.writerow([t.strftime("%Y-%m-%d %H:%M"), f"{np.mean(v):.4f}", len(v)])
    log(f"gözlem CSV: {out} ({len(per_hour)} saat, sensör {sensor})")
    return out

# ---------- model
def model_series():
    """Tüm aylık yüzey dosyalarından Menteş'e en yakın düğümün saatlik su seviyesi."""
    import netCDF4
    fs = sorted(PROC.glob("schism_surface_*.nc"))
    if not fs: raise SystemExit("[70] data/processed/schism_surface_*.nc yok")
    t_all, e_all, node = [], [], None
    for f in fs:
        d = netCDF4.Dataset(f)
        if node is None:
            x = d.variables["SCHISM_hgrid_node_x"][:]; y = d.variables["SCHISM_hgrid_node_y"][:]
            dist = np.hypot((x - LON) * np.cos(np.deg2rad(LAT)), y - LAT) * 111.0
            node = int(np.argmin(dist))
            log(f"en yakın düğüm #{node} ({float(x[node]):.4f}/{float(y[node]):.4f}), {1000*dist[node]:.0f} m; "
                f"derinlik {float(d.variables['depth'][node]):.1f} m")
        tv = d.variables["time"]
        epoch = datetime.strptime(tv.units.split("since")[1].strip()[:19], "%Y-%m-%d %H:%M:%S")
        t_all += [epoch + timedelta(seconds=float(s)) for s in tv[:]]
        e_all += list(np.asarray(d.variables["elev"][:, node], dtype=float))
        d.close()
    o = np.argsort(t_all)
    return [t_all[i] for i in o], np.array(e_all)[o]

# ---------- karşılaştırma
def metrics(o, m):
    oa, ma = o - o.mean(), m - m.mean()          # datum farkı çıkarılır
    bias = float(m.mean() - o.mean())
    rmse = float(np.sqrt(np.mean((m - o) ** 2)))
    crmse = float(np.sqrt(np.mean((ma - oa) ** 2)))
    r = float(np.corrcoef(oa, ma)[0, 1])
    return {"n": len(o), "bias_m": bias, "rmse_m": rmse, "crmse_m": crmse, "r": r,
            "std_obs_m": float(o.std()), "std_mod_m": float(m.std()), "std_orani": float(m.std() / o.std())}

def harmonics(t, y, lat):
    try: import utide
    except ImportError: return None
    tn = np.array([(ti - datetime(1, 1, 1)).total_seconds() / 86400 + 1 for ti in t])
    c = utide.solve(tn, y - y.mean(), lat=lat, method="ols", conf_int="none", verbose=False)
    return {n: (float(a), float(g)) for n, a, g in zip(c.name, c.A, c.g) if n in ("M2", "S2", "K1", "O1", "N2", "P1")}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true"); ap.add_argument("--force", action="store_true")
    ap.add_argument("--start", default=None); ap.add_argument("--end", default=None)
    a = ap.parse_args()
    P = params(); Y = P.get("year_run", {})
    d0 = date.fromisoformat(a.start or str(Y.get("start", "2025-09-01")))
    d1 = date.fromisoformat(a.end or str(Y.get("end", "2026-09-01")))
    if a.download:
        download(d0, d1, a.force); build_obs_csv(); return
    obs_csv = PROC / f"obs_sealevel_{CODE}.csv"
    if not obs_csv.exists(): obs_csv = build_obs_csv()
    O = {datetime.strptime(r["time"], "%Y-%m-%d %H:%M"): float(r["slevel_m"])
         for r in csv.DictReader(open(obs_csv, encoding="utf-8"))}
    mt, me = model_series()
    M = dict(zip(mt, me))
    ort = sorted(set(O) & set(M))
    if len(ort) < 24: raise SystemExit(f"[70] ortak saat çok az ({len(ort)}) — gözlem dönemi model dönemiyle örtüşmüyor olabilir")
    o = np.array([O[t] for t in ort]); m = np.array([M[t] for t in ort])
    st = metrics(o, m)
    L = [f"SCHISM ↔ Menteş mareografı (IOC `{CODE}`, {LAT}°K {LON}°D)",
         f"ortak saat: {st['n']} ({ort[0]:%Y-%m-%d} → {ort[-1]:%Y-%m-%d}); model {len(mt)} sa, gözlem {len(O)} sa", "",
         f"  bias (model − gözlem)      {st['bias_m']:+.3f} m   (datum farkı; karşılaştırmada çıkarıldı)",
         f"  RMSE (ham)                 {st['rmse_m']:.3f} m",
         f"  merkezlenmiş RMSE          {st['crmse_m']:.3f} m   ← asıl ölçüt",
         f"  Pearson r                  {st['r']:.3f}",
         f"  std gözlem / model         {st['std_obs_m']:.3f} / {st['std_mod_m']:.3f} m  (oran {st['std_orani']:.2f})"]
    ho, hm = harmonics(ort, o, LAT), harmonics(ort, m, LAT)
    if ho and hm:
        L += ["", "gelgit harmonikleri (genlik m / faz °):", f"  {'bileşen':8s} {'gözlem':>16s} {'model':>16s}"]
        for k in ("M2", "S2", "K1", "O1", "N2", "P1"):
            if k in ho and k in hm:
                L.append(f"  {k:8s} {ho[k][0]:8.4f} / {ho[k][1]:5.1f} {hm[k][0]:8.4f} / {hm[k][1]:5.1f}")
    else:
        L += ["", "(utide kurulu değil — harmonik karşılaştırma atlandı: pip install utide)"]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sealevel_summary.txt").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        oa, ma = o - o.mean(), m - m.mean()
        k = min(len(ort), 24 * 30)
        fig, ax = plt.subplots(2, 1, figsize=(12, 7))
        ax[0].plot(ort[:k], oa[:k], lw=0.9, label="Menteş (gözlem)")
        ax[0].plot(ort[:k], ma[:k], lw=0.9, label="SCHISM")
        ax[0].set_ylabel("su seviyesi anomalisi (m)"); ax[0].legend(); ax[0].grid(alpha=.3)
        ax[0].set_title(f"İlk 30 gün — crmse {st['crmse_m']:.3f} m, r {st['r']:.3f}")
        ax[1].hexbin(oa, ma, gridsize=60, mincnt=1, cmap="viridis")
        lim = max(abs(oa).max(), abs(ma).max())
        ax[1].plot([-lim, lim], [-lim, lim], "r-", lw=1)
        ax[1].set_xlabel("gözlem (m)"); ax[1].set_ylabel("model (m)"); ax[1].set_title("tüm yıl")
        fig.tight_layout(); fig.savefig(OUT / "sealevel_series.png", dpi=130); plt.close(fig)
        log("grafik:", OUT / "sealevel_series.png")
    except ImportError:
        log("matplotlib yok — grafik atlandı")

if __name__ == "__main__":
    main()
