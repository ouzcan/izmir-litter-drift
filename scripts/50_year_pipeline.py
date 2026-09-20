"""Yıllık SCHISM 3B koşusu — aylık parçalar halinde (config/model_params.yaml → year_run).

Her ay ayrı koşu klasörü (runs/schism/y2025-09 …): ayın 1'inden `spinup_days` gün önce CMEMS T/S profiliyle soğuk
başlar, ay sonuna kadar koşar; ısınma payı atılıp yüzey akıntısı `data/processed/schism_surface_YYYY-MM.nc` olarak
saklanır (OpenDrift bu dosyaları `schism_surface_*.nc` deseniyle birlikte okur), ham çıktı silinir (~5 GB/ay).

Aşamalar (Windows, conda 'litter'):
    python scripts/50_year_pipeline.py plan                 # ay listesi, süre/disk tahmini
    python scripts/50_year_pipeline.py check                # Copernicus ürün zaman kapsamı (indirmeden önce)
    python scripts/50_year_pipeline.py download             # tüm dönem CMEMS + ERA5 (ERA5 ay ay istek; 30–60 dk)
    python scripts/50_year_pipeline.py prepare [--month 2025-09]   # her ay: 33 --mode 3d --lean --out_min 60 + 32 all 3d
    python scripts/50_year_pipeline.py script               # runs/schism/run_year.sh (WSL'de: bash runs/schism/run_year.sh)
    python scripts/50_year_pipeline.py post --month 2025-09 # 40 (ısınma payı atılır) + ham çıktıyı sil  (run_year.sh WSL'den çağırır)
    python scripts/50_year_pipeline.py status
WSL tarafı bir kez: python3 -m venv ~/odenv && ~/odenv/bin/pip install numpy xarray netcdf4 pyyaml scipy dask
"""
from __future__ import annotations
import argparse, glob, json, shutil, subprocess, sys
from datetime import date, datetime, timedelta
from pathlib import Path

from common import ROOT, RUNS, PROC, RAW, params

P = params(); Y = P.get("year_run", {})
START = date.fromisoformat(str(Y.get("start", "2025-09-01"))); END = date.fromisoformat(str(Y.get("end", "2026-09-01")))
SPIN = int(Y.get("spinup_days", 5)); PREFIX = Y.get("run_prefix", "y"); NPROC = int(Y.get("nproc", 18))
OUT_MIN = int(Y.get("output_min", 60)); SCR = ROOT / "scripts"; PY = sys.executable

def log(*a): print("[50]", *a, flush=True)

def months():
    out = []; d = START
    while d < END:
        nxt = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
        out.append((f"{d:%Y-%m}", d, min(nxt, END))); d = nxt
    return out

def seg(m):
    """(koşu adı, koşu başlangıcı, gün sayısı, ay başı, ay sonu)"""
    ym, m0, m1 = m
    s0 = m0 - timedelta(days=SPIN)
    return f"{PREFIX}{ym}", s0, (m1 - s0).days, m0, m1

def run(cmd):
    log("$", " ".join(str(c) for c in cmd))
    r = subprocess.run([str(c) for c in cmd], cwd=str(ROOT))
    if r.returncode != 0: raise SystemExit(f"komut başarısız ({r.returncode})")

def cmd_plan(a):
    ms = months(); tot = 0
    log(f"dönem {START} → {END}: {len(ms)} ay, ısınma {SPIN} gün, çıktı {OUT_MIN} dk, {NPROC} çekirdek")
    for m in ms:
        name, s0, nd, m0, m1 = seg(m); tot += nd
        print(f"  {name:10s} koşu {s0} +{nd} gün  (ay {m0}..{m1})")
    est_h = tot / 7 * float(Y.get("hours_per_7days", 0.45))
    print(f"toplam {tot} model günü; tahmini süre ≈ {est_h:.0f} saat ({Y.get('hours_per_7days', 0.45)} sa/7 gün varsayımı)")
    print(f"disk: ham çıktı ≤ ~{5 * 60 / OUT_MIN:.0f} GB/ay (ay bitince silinir); yüzey dosyaları ≈ {0.66 * 60 / OUT_MIN:.1f} GB/ay → {0.66 * 60 / OUT_MIN * len(ms):.0f} GB/yıl")

def cmd_check(a):
    import copernicusmarine as cm
    CM = P.get("dflowfm", {}).get("cmems_datasets", {})
    for var, ds_id in sorted(set(CM.items())):
        try:
            d = cm.describe(dataset_id=ds_id, disable_progress_bar=True)
            j = d.model_dump() if hasattr(d, "model_dump") else json.loads(d.json() if hasattr(d, "json") else json.dumps(d))
            spans = []
            def walk(o):
                if isinstance(o, dict):
                    if o.get("coordinate_id") == "time" and o.get("minimum_value") is not None:
                        spans.append((o["minimum_value"], o["maximum_value"]))
                    for v in o.values(): walk(v)
                elif isinstance(o, list):
                    for v in o: walk(v)
            walk(j)
            def fmt(v):
                try: return datetime.utcfromtimestamp(float(v) / 1000).strftime("%Y-%m-%d") if float(v) > 1e11 else str(v)
                except Exception: return str(v)
            if spans: print(f"  {var:7s} {ds_id}: {fmt(min(s[0] for s in spans))} → {fmt(max(s[1] for s in spans))}")
            else: print(f"  {var:7s} {ds_id}: zaman kapsamı okunamadı (describe çıktısı değişmiş olabilir)")
        except Exception as e:  # noqa: BLE001
            print(f"  {var:7s} {ds_id}: describe hatası: {e}")
    print(f"gereken: {START - timedelta(days=SPIN + 1)} → {END + timedelta(days=1)}. Kapsam yetmiyorsa model_params.yaml'da 'my'/'myint' kimliklerine geç.")

def cmd_download(a):
    s0 = START - timedelta(days=SPIN); run([PY, SCR / "32_forcing_to_schism.py", "download", "--start", s0.isoformat(), "--end", END.isoformat()])

def cmd_prepare(a):
    for m in months():
        name, s0, nd, m0, m1 = seg(m)
        if a.month and m[0] != a.month: continue
        d = RUNS / "schism" / name
        if (d / "outputs" / "done").exists() and not a.force: log(name, "bitmiş, atla"); continue
        run([PY, SCR / "33_schism_setup.py", "--run", name, "--mode", "3d", "--start", s0.isoformat(), "--days", str(nd), "--lean", "--out_min", str(OUT_MIN)])
        run([PY, SCR / "32_forcing_to_schism.py", "all", "--run", name, "--start", s0.isoformat(), "--end", m1.isoformat(), "--mode", "3d"])
    log("hazır. Sonra: python scripts/50_year_pipeline.py script  → WSL'de: bash runs/schism/run_year.sh")

def wsl_path(p: Path) -> str:
    s = str(p.resolve()).replace("\\", "/")
    if len(s) > 1 and s[1] == ":": s = f"/mnt/{s[0].lower()}{s[2:]}"
    return s

def cmd_script(a):
    root = wsl_path(ROOT); ns = 3
    lines = ["#!/bin/bash", "# Yıllık SCHISM koşusu — WSL Ubuntu'da: bash runs/schism/run_year.sh   (yeniden başlatılabilir: biten aylar atlanır)",
             f"ROOT={root}", f"NP={NPROC + ns}", "PSCHISM=${PSCHISM:-$HOME/schism/pschism}", "PYW=${PYW:-$HOME/odenv/bin/python}",
             'if [ ! -x "$PYW" ]; then echo "WSL python ortamı yok: python3 -m venv ~/odenv && ~/odenv/bin/pip install numpy xarray netcdf4 pyyaml scipy dask"; exit 1; fi',
             "cd $ROOT || exit 1", ""]
    for m in months():
        name, s0, nd, m0, m1 = seg(m)
        lines += [f"# ---- {name}: {s0} +{nd} gün",
                  f"if [ -f runs/schism/{name}/outputs/done ]; then echo '{name} tamam, atla'; else",
                  f"  echo \"$(date +%H:%M) {name} başlıyor\"; cd runs/schism/{name} && rm -rf outputs/* && mpirun -np $NP $PSCHISM {ns} > run.log 2>&1; cd $ROOT",
                  f"  grep -q 'Run completed successfully' runs/schism/{name}/outputs/mirror.out || {{ echo '{name} HATA — run.log / outputs/fatal.error'; exit 1; }}",
                  f"  touch runs/schism/{name}/outputs/done",
                  f"  $PYW scripts/50_year_pipeline.py post --month {m[0]} || exit 1",
                  "fi", ""]
    lines.append('echo "yıl tamamlandı: $(ls data/processed/schism_surface_*.nc | wc -l) aylık yüzey dosyası"')
    out = RUNS / "schism" / "run_year.sh"; out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    log("yazıldı:", out, "→ WSL:  bash", wsl_path(out))

def cmd_post(a):
    m = next((x for x in months() if x[0] == a.month), None)
    if not m: raise SystemExit(f"ay yok: {a.month}")
    name, s0, nd, m0, m1 = seg(m); d = RUNS / "schism" / name
    PROC.mkdir(parents=True, exist_ok=True)
    out = PROC / f"schism_surface_{m[0]}.nc"
    run([PY, SCR / "40_schism_to_opendrift.py", "--run", name, "--layer", "top", "--t0", m0.isoformat(), "--t1", m1.isoformat(), "--out", str(out)])
    if out.exists() and out.stat().st_size > 1e6 and not a.keep:
        n = 0
        for f in glob.glob(str(d / "outputs" / "*.nc")):
            Path(f).unlink(); n += 1
        for f in glob.glob(str(d / "outputs" / "local_to_global_*")): Path(f).unlink()
        log(f"{name}: {n} ham çıktı dosyası silindi; yüzey dosyası {out.name} ({out.stat().st_size/1e6:.0f} MB)")

def cmd_status(a):
    for m in months():
        name, s0, nd, m0, m1 = seg(m); d = RUNS / "schism" / name; surf = PROC / f"schism_surface_{m[0]}.nc"
        st = "yüzey dosyası hazır" if surf.exists() else ("koşu bitti, post bekliyor" if (d / "outputs" / "done").exists()
              else ("girdiler hazır" if (d / "sflux").exists() else ("kurulum var" if d.exists() else "—")))
        mir = d / "outputs" / "mirror.out"
        if not surf.exists() and mir.exists():
            try:
                last = [l for l in mir.read_text(errors="ignore").splitlines() if "TIME STEP" in l][-1].split()
                st += f" (adım {last[2].rstrip(';')})"
            except Exception: pass
        print(f"  {name:10s} {st}")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["plan", "check", "download", "prepare", "script", "post", "status"])
    ap.add_argument("--month", default=None); ap.add_argument("--force", action="store_true"); ap.add_argument("--keep", action="store_true", help="post: ham çıktıyı silme")
    a = ap.parse_args()
    {"plan": cmd_plan, "check": cmd_check, "download": cmd_download, "prepare": cmd_prepare, "script": cmd_script, "post": cmd_post, "status": cmd_status}[a.cmd](a)

if __name__ == "__main__":
    main()
