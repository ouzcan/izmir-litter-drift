"""Doğrulama Katman 1b — rüzgâr: ERA5 ↔ LTBJ (İzmir Adnan Menderes) METAR.

İstasyon: LTBJ, 38,2667°K 27,1500°D, rakım 120 m. Kaynak: Iowa State IEM ASOS arşivi (ücretsiz, hesapsız, saatlik).
UYARI: istasyon iç kesimde ve 120 m rakımda — körfez üzerindeki imbatı tam temsil etmez. Bu karşılaştırma
ERA5'in ZAMANSAL doğruluğunu (geçişler, fırtına zamanlaması, yön dağılımı) sınar; mutlak deniz üstü hız
kalibrasyonu için tek başına yeterli sayılmamalı. (LTBL Çiğli meta verisi aktif görünse de METAR yayınlamıyor.)

İki aşama (indirme ayrı, çünkü IEM bazı ağlardan engelli):
    python scripts/71_validate_wind.py --download
    python scripts/71_validate_wind.py

Çıktı: data/raw/obs/asos_LTBJ.csv, docs/sonuclar/dogrulama/wind_summary.txt, wind_scatter.png
"""
from __future__ import annotations
import argparse, csv, io
from datetime import date, datetime, timedelta
from pathlib import Path
import numpy as np

from common import ROOT, RAW, params

OBS = RAW / "obs"
OUT = ROOT / "docs" / "sonuclar" / "dogrulama"
ST, SLON, SLAT = "LTBJ", 27.1500, 38.2667
KT = 0.514444

def log(*a): print("[71]", *a, flush=True)

def download(d0: date, d1: date):
    import urllib.request
    OBS.mkdir(parents=True, exist_ok=True)
    url = ("https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?"
           f"station={ST}&data=sknt&data=drct&data=gust&tz=Etc/UTC&format=onlycomma&latlon=no"
           f"&missing=M&trace=T&direct=no&report_type=3&report_type=4"
           f"&year1={d0.year}&month1={d0.month}&day1={d0.day}&year2={d1.year}&month2={d1.month}&day2={d1.day}")
    log("indiriliyor:", url[:100] + "…")
    with urllib.request.urlopen(url, timeout=300) as r: txt = r.read().decode("utf-8", "replace")
    f = OBS / f"asos_{ST}.csv"; f.write_text(txt, encoding="utf-8")
    n = sum(1 for l in txt.splitlines() if l and not l.startswith("#"))
    log(f"{f} ({n} satır)")
    if n < 100: log("UYARI: satır sayısı çok az — istasyon bu dönemde veri yayınlamıyor olabilir")

def read_obs():
    f = OBS / f"asos_{ST}.csv"
    if not f.exists(): raise SystemExit(f"[71] {f} yok — önce --download")
    txt = "\n".join(l for l in f.read_text(encoding="utf-8").splitlines() if not l.startswith("#"))
    out = {}
    for r in csv.DictReader(io.StringIO(txt)):
        try:
            t = datetime.strptime(r["valid"][:16], "%Y-%m-%d %H:%M")
            t = (t + timedelta(minutes=30)).replace(minute=0, second=0)      # :50 kaydı → tam saate yuvarla
            sp = float(r["sknt"]) * KT; dr = float(r["drct"])
        except (KeyError, ValueError, TypeError): continue
        if not (np.isfinite(sp) and np.isfinite(dr)) or sp < 0: continue
        th = np.deg2rad(dr)
        out[t] = (-sp * np.sin(th), -sp * np.cos(th))        # meteorolojik yön (geldiği yön) → u,v vektörü
    return out

def read_era5():
    import netCDF4
    fs = sorted(RAW.glob("forcing/era5_????-??-??_????-??-??.nc"))
    fs = [f for f in fs if "part" not in f.name]
    if not fs: fs = sorted(RAW.glob("forcing/era5_part_*.nc"))
    if not fs: raise SystemExit("[71] data/raw/forcing/era5_*.nc yok")
    out = {}
    for f in fs:
        d = netCDF4.Dataset(f)
        lon = np.asarray(d.variables["longitude"][:], float); lat = np.asarray(d.variables["latitude"][:], float)
        tv = d.variables["valid_time"] if "valid_time" in d.variables else d.variables["time"]
        ep = datetime(1970, 1, 1)
        u = np.asarray(d.variables["u10"][:], float); v = np.asarray(d.variables["v10"][:], float)
        # çift doğrusal ara değer — en yakın hücre yerine (ERA5 0,25°, istasyon hücre kenarına yakın)
        ix = np.searchsorted(lon, SLON) - 1; ix = min(max(ix, 0), len(lon) - 2)
        des = lat[0] > lat[-1]
        la = lat[::-1] if des else lat
        iy = np.searchsorted(la, SLAT) - 1; iy = min(max(iy, 0), len(la) - 2)
        fx = (SLON - lon[ix]) / (lon[ix + 1] - lon[ix]); fy = (SLAT - la[iy]) / (la[iy + 1] - la[iy])
        j0, j1 = (len(lat) - 1 - iy, len(lat) - 2 - iy) if des else (iy, iy + 1)
        for k, s in enumerate(np.asarray(tv[:], float)):
            t = ep + timedelta(seconds=float(s))
            def bl(a):
                return ((1-fx)*(1-fy)*a[j0, ix] + fx*(1-fy)*a[j0, ix+1] + (1-fx)*fy*a[j1, ix] + fx*fy*a[j1, ix+1])
            out[t] = (float(bl(u[k])), float(bl(v[k])))
        log(f"{f.name}: {len(tv)} saat; ara değer köşesi lon {lon[ix]:.2f}-{lon[ix+1]:.2f}, lat {la[iy]:.2f}-{la[iy+1]:.2f}")
        d.close()
    return out

def circ_mean_diff(o_dir, m_dir):
    d = (m_dir - o_dir + 180) % 360 - 180
    return float(np.mean(d)), float(np.sqrt(np.mean(d ** 2)))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--start", default=None); ap.add_argument("--end", default=None)
    a = ap.parse_args()
    P = params(); Y = P.get("year_run", {})
    d0 = date.fromisoformat(a.start or str(Y.get("start", "2025-09-01")))
    d1 = date.fromisoformat(a.end or str(Y.get("end", "2026-09-01")))
    if a.download: download(d0, d1); return
    O, M = read_obs(), read_era5()
    ort = sorted(set(O) & set(M))
    ort = [t for t in ort if d0 <= t.date() < d1]
    if len(ort) < 24: raise SystemExit(f"[71] ortak saat çok az ({len(ort)})")
    ou = np.array([O[t][0] for t in ort]); ov = np.array([O[t][1] for t in ort])
    mu = np.array([M[t][0] for t in ort]); mv = np.array([M[t][1] for t in ort])
    osp, msp = np.hypot(ou, ov), np.hypot(mu, mv)
    od = (np.rad2deg(np.arctan2(-ou, -ov)) + 360) % 360
    md = (np.rad2deg(np.arctan2(-mu, -mv)) + 360) % 360
    ok = osp > 1.0                                        # sakin saatlerde yön anlamsız
    dbias, drmse = circ_mean_diff(od[ok], md[ok])
    L = [f"ERA5 ↔ {ST} METAR (İzmir Adnan Menderes, {SLAT}°K {SLON}°D, 120 m)",
         f"ortak saat: {len(ort)} ({ort[0]:%Y-%m-%d} → {ort[-1]:%Y-%m-%d})", "",
         f"  hız  bias (ERA5 − METAR)   {float(msp.mean() - osp.mean()):+.2f} m/s",
         f"  hız  RMSE                  {float(np.sqrt(np.mean((msp - osp) ** 2))):.2f} m/s",
         f"  hız  r                     {float(np.corrcoef(osp, msp)[0, 1]):.3f}",
         f"  ortalama hız  METAR/ERA5   {float(osp.mean()):.2f} / {float(msp.mean()):.2f} m/s",
         "",
         f"  u bileşeni  bias / RMSE    {float(mu.mean()-ou.mean()):+.2f} / {float(np.sqrt(np.mean((mu-ou)**2))):.2f} m/s",
         f"  v bileşeni  bias / RMSE    {float(mv.mean()-ov.mean()):+.2f} / {float(np.sqrt(np.mean((mv-ov)**2))):.2f} m/s",
         f"  vektör korelasyonu (u,v)   {float(np.corrcoef(np.r_[ou, ov], np.r_[mu, mv])[0, 1]):.3f}",
         "",
         f"  yön  bias / RMSE (>1 m/s)  {dbias:+.1f}° / {drmse:.1f}°   ({int(ok.sum())} saat)",
         "",
         "NOT: LTBJ iç kesimde ve 120 m rakımda; körfez üzerindeki imbatı tam temsil etmez.",
         "Bu karşılaştırma ERA5'in zamansal doğruluğunu sınar, mutlak deniz üstü hız kalibrasyonunu değil."]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "wind_summary.txt").write_text("\n".join(L), encoding="utf-8"); print("\n".join(L))
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(11, 5))
        ax[0].hexbin(osp, msp, gridsize=40, mincnt=1, cmap="viridis")
        lim = max(osp.max(), msp.max()); ax[0].plot([0, lim], [0, lim], "r-", lw=1)
        ax[0].set_xlabel("METAR hız (m/s)"); ax[0].set_ylabel("ERA5 hız (m/s)"); ax[0].set_title("hız")
        ax[1].hexbin(od[ok], md[ok], gridsize=40, mincnt=1, cmap="viridis")
        ax[1].plot([0, 360], [0, 360], "r-", lw=1)
        ax[1].set_xlabel("METAR yön (°)"); ax[1].set_ylabel("ERA5 yön (°)"); ax[1].set_title("yön (>1 m/s)")
        fig.tight_layout(); fig.savefig(OUT / "wind_scatter.png", dpi=130); plt.close(fig)
        log("grafik:", OUT / "wind_scatter.png")
    except ImportError:
        log("matplotlib yok — grafik atlandı")

if __name__ == "__main__":
    main()
