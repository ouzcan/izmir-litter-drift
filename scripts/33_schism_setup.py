"""SCHISM koşu klasörünü hazırla: param.nml, vgrid.in, bctides.in, drag.gr3 (+ 2D/3D seçimi).

Kullanım:
    python scripts/33_schism_setup.py --mode smoke        # 2D barotropik, zorlama yok, 6 saat: ağ/sınır sağlık testi
    python scripts/33_schism_setup.py --mode 2d --start 2026-09-06 --days 7
    python scripts/33_schism_setup.py --mode 3d --start 2026-09-06 --days 7 --nvrt 11
Girdi: runs/schism/<ad>/hgrid.gr3 (31_mesh_to_schism.py), param şablonu: config/schism/param.nml.template
       (yoksa SCHISM kaynak kodundaki sample_inputs/param.nml verilir: --template)
Çıktı: runs/schism/<ad>/{param.nml, vgrid.in, bctides.in, drag.gr3, outputs/}
"""
from __future__ import annotations
import argparse, re, shutil
from pathlib import Path
from datetime import datetime

import numpy as np

from common import ROOT, RUNS, CFG, params

S = params().get("schism", {})

def log(*a): print("[33]", *a, flush=True)

def read_hgrid(p: Path):
    lines = p.read_text().splitlines()
    ne, nn = map(int, lines[1].split())
    dep = np.array([float(l.split()[3]) for l in lines[2:2 + nn]])
    i = 2 + nn + ne
    nope = int(lines[i].split()[0]); j = i + 2; opens = []
    for _ in range(nope):
        n = int(lines[j].split()[0]); opens.append(n); j += 1 + n
    return ne, nn, dep, opens

def set_param(text: str, key: str, value) -> str:
    """param.nml içinde `key = ...` satırını değiştirir (yorum korunur); yoksa ekler."""
    pat = re.compile(rf"^(\s*{re.escape(key)}\s*=\s*)([^!\n]*)(.*)$", re.M)
    val = str(value)
    if pat.search(text):
        return pat.sub(lambda m: f"{m.group(1)}{val} {m.group(3)}".rstrip(), text, count=1)
    return text.rstrip() + f"\n  {key} = {val}\n"

def write_vgrid(out: Path, nvrt: int):
    if nvrt <= 2:
        txt = "2 !ivcor (2: SZ)\n2 1 1.e6 !nvrt, kz, h_s\nZ levels\n1 -1.e6\nS levels\n40. 1. 1.e-4 !h_c, theta_b, theta_f\n1 -1.\n2 0.\n"
    else:
        # saf sigma (kz=1, h_s büyük); yüzeye doğru sıklaşan dağılım (theta_f=3) — yüzey akıntısı için
        sig = -np.linspace(1, 0, nvrt)
        lines = ["2 !ivcor (2: SZ)", f"{nvrt} 1 1.e6 !nvrt, kz, h_s", "Z levels", "1 -1.e6", "S levels", "20. 0.7 3. !h_c, theta_b, theta_f"]
        lines += [f"{k+1} {s:.6f}" for k, s in enumerate(sig)]
        txt = "\n".join(lines) + "\n"
    (out / "vgrid.in").write_text(txt)

def write_bctides(out: Path, start: datetime, opens: list[int], mode: str):
    lines = [start.strftime("%m/%d/%Y %H:%M:%S UTC"), "0 40. ntip", "0 nbfr", f"{len(opens)} nope"]
    for n in opens:
        if mode == "smoke":
            lines.append(f"{n} 2 0 0 0 !elev const, no flow, no T/S"); lines.append("0.0 !eth")
        elif mode == "2d":
            lines.append(f"{n} 4 -4 0 0 !elev2D.th.nc + uv3D.th.nc (gevşetmeli)")
            lines.append(f"{S.get('uv_relax_in', 1.0)} {S.get('uv_relax_out', 0.3)} !inflow, outflow relax (tek satır)")
        else:
            lines.append(f"{n} 4 -4 4 4 !elev2D, uv3D (gevşetmeli), TEM_3D, SAL_3D .th.nc")
            lines.append(f"{S.get('uv_relax_in', 1.0)} {S.get('uv_relax_out', 0.3)} !inflow, outflow relax (uv)")
            lines.append("1. !tobc"); lines.append("1. !sobc")
    (out / "bctides.in").write_text("\n".join(lines) + "\n")

def write_const_prop(out: Path, name: str, ne: int, value):
    """Eleman tabanlı .prop dosyası (tvd.prop vb.): 'eleman_no değer'."""
    with open(out / name, "w") as fh:
        fh.writelines(f"{i+1} {value}\n" for i in range(ne))

def write_const_gr3(out: Path, name: str, hgrid: Path, value: float):
    lines = hgrid.read_text().splitlines()
    ne, nn = map(int, lines[1].split())
    with open(out / name, "w") as fh:
        fh.write(f"{name} constant {value}\n{ne} {nn}\n")
        for l in lines[2:2 + nn]:
            p = l.split(); fh.write(f"{p[0]} {p[1]} {p[2]} {value}\n")
        fh.writelines(l + "\n" for l in lines[2 + nn:2 + nn + ne])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=S.get("run_name", "izmir"))
    ap.add_argument("--mode", choices=["smoke", "2d", "3d"], default="smoke")
    ap.add_argument("--start", default="2026-09-06")
    ap.add_argument("--days", type=float, default=None)
    ap.add_argument("--dt", type=float, default=float(S.get("dt_s", 60)))
    ap.add_argument("--nvrt", type=int, default=None)
    ap.add_argument("--template", default=None, help="param.nml şablonu (varsayılan config/schism/param.nml.template)")
    a = ap.parse_args()
    out = RUNS / "schism" / a.run
    out.mkdir(parents=True, exist_ok=True)
    hg = out / "hgrid.gr3"
    if not hg.exists():
        # ayrı bir koşu adı (örn. izmir3d) için ağı varsayılan koşudan kopyala
        src = RUNS / "schism" / S.get("run_name", "izmir")
        if (src / "hgrid.gr3").exists() and src != out:
            for f in ("hgrid.gr3", "hgrid.ll"): shutil.copy(src / f, out / f)
            log(f"hgrid.gr3/hgrid.ll {src.name} koşusundan kopyalandı")
        else:
            raise SystemExit("hgrid.gr3 yok — önce 31_mesh_to_schism.py")
    ne, nn, dep, opens = read_hgrid(hg)
    start = datetime.fromisoformat(a.start)
    days = a.days if a.days is not None else (0.25 if a.mode == "smoke" else 7)
    nvrt = a.nvrt if a.nvrt else (2 if a.mode != "3d" else int(S.get("nvrt3d", 11)))
    tpl = Path(a.template) if a.template else (CFG / "schism" / "param.nml.template")
    if not tpl.exists(): raise SystemExit(f"param şablonu yok: {tpl} (SCHISM kaynak: sample_inputs/param.nml)")
    t = tpl.read_text()

    spool_s = 1800; nspool = int(round(spool_s / a.dt)); ihfskip = nspool * 24   # 30 dk çıktı, 12 saatlik yığın (out2d_N.nc)
    kv = dict(ipre=0, ibc=1 if a.mode != "3d" else 0, ibtp=0 if a.mode != "3d" else 1,
              rnday=days, dt=a.dt, nspool=nspool, ihfskip=ihfskip,
              start_year=start.year, start_month=start.month, start_day=start.day, start_hour=start.hour, utc_start=0,
              ics=2, ncor=1, ihot=0, dramp=1.0, nchi=0, ishapiro=1, shapiro0=0.5, indvel=0,
              ihorcon=int(S.get("ihorcon", 1)), hvis_coef0=float(S.get("hvis_coef0", 0.025)),
              nws=0 if a.mode == "smoke" else 2, iwind_form=1, ihconsv=0, isconsv=0, itur=3 if a.mode == "3d" else 0,
              h0=0.05, rmaxvel=5.0, inunfl=0, nhot=0, iout_sta=0,
              slam0=27.0, sfea0=38.5, thetai=0.6, dtb_max=30.0, dtb_min=10.0,
              ic_elev=0, flag_ic=1)
    if a.mode == "3d":
        # ihconsv=1 (ısı akısı) sflux_rad_1.N.nc (kısa/uzun dalga) ister; ERA5 ssrd/strd indirilene kadar kapalı.
        kv.update({"flag_ic(1)": 2, "flag_ic(2)": 2,   # ts.ic: dikey profil (32 yazar)
                    "ihconsv": int(S.get("ihconsv3d", 0)), "isconsv": 0, "itr_met": 3, "h_tvd": 5.0})
    for k, v in kv.items(): t = set_param(t, k, v)
    # çıktılar: su seviyesi, derinlik ortalamalı hız, (3D) yatay hız, T, S
    d3 = 1 if a.mode == "3d" else 0
    for k, v in {"iof_hydro(1)": 1, "iof_hydro(16)": 1, "iof_hydro(14)": d3,           # elev, derinlik-ort. hız, rüzgâr (2B)
                 "iof_hydro(26)": d3, "iof_hydro(18)": d3, "iof_hydro(19)": d3, "iof_hydro(25)": d3,  # 3B: yatay hız, T, S, z
                 "iof_hydro(15)": 0}.items():
        t = set_param(t, k, v)
    (out / "param.nml").write_text(t)
    write_vgrid(out, nvrt)
    write_bctides(out, start, opens, a.mode)
    write_const_gr3(out, "drag.gr3", hg, float(S.get("drag_cd", 0.0025)))
    if a.mode != "smoke":
        write_const_gr3(out, "windrot_geo2proj.gr3", hg, 0.0)
    if a.mode == "3d":
        write_const_gr3(out, "diffmin.gr3", hg, 1e-6); write_const_gr3(out, "diffmax.gr3", hg, 1.0)
        write_const_gr3(out, "albedo.gr3", hg, 0.06); write_const_gr3(out, "watertype.gr3", hg, 1)
        write_const_prop(out, "tvd.prop", ne, 1)     # itr_met=3: TVD her elemanda (h_tvd'den sığda kod zaten upwind kullanır)
    (out / "outputs").mkdir(exist_ok=True)
    log(f"{a.mode}: {nn} düğüm, {ne} eleman, açık sınır {opens}, nvrt={nvrt}, dt={a.dt}s, {days} gün, nspool={nspool}, ihfskip={ihfskip}")
    nscribe = 6 if a.mode == "3d" else 2   # scribe sayısı ≥ 3B çıktı değişkeni sayısı (+1): horizontalVelX/Y, T, S, zCoordinates
    log(f"koş (WSL): cd {out} && rm -rf outputs/* && mpirun -np <hesap çekirdeği + {nscribe}> ~/schism/pschism {nscribe}")

if __name__ == "__main__":
    main()
