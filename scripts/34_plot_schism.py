"""SCHISM out2d_*.nc çıktısını özetle ve çiz: su seviyesi, derinlik-ort. hız, iç körfez ok haritası.

Kullanım:
    python scripts/34_plot_schism.py [--run izmir] [--t -1]
Çıktı: runs/schism/<ad>/plots/{summary.txt, speed_elev_tXX.png, ic_korfez_tXX.png}
"""
from __future__ import annotations
import argparse, glob, warnings
from pathlib import Path
import numpy as np
import xarray as xr

from common import RUNS, params

warnings.filterwarnings("ignore")
S = params().get("schism", {})
COSLAT = np.cos(np.deg2rad(38.6))

def tri_from_hgrid(p: Path):
    lines = p.read_text().splitlines(); ne, nn = map(int, lines[1].split())
    tris = []
    for l in lines[2 + nn:2 + nn + ne]:
        q = l.split(); n = [int(v) - 1 for v in q[2:2 + int(q[1])]]
        tris.append([n[0], n[1], n[2]])
        if len(n) == 4: tris.append([n[0], n[2], n[3]])
    return np.array(tris)

def main():
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt, matplotlib.tri as mtri
    ap = argparse.ArgumentParser(); ap.add_argument("--run", default=S.get("run_name", "izmir")); ap.add_argument("--t", type=int, default=-1)
    a = ap.parse_args()
    run = RUNS / "schism" / a.run; out = run / "plots"; out.mkdir(exist_ok=True)
    files = sorted(glob.glob(str(run / "outputs" / "out2d_*.nc")), key=lambda f: int(Path(f).stem.split("_")[1]))
    ds = xr.concat([xr.open_dataset(f) for f in files], dim="time", data_vars="all")
    x = ds["SCHISM_hgrid_node_x"].values; y = ds["SCHISM_hgrid_node_y"].values
    e = ds["elevation"].values; u = ds["depthAverageVelX"].values; v = ds["depthAverageVelY"].values; sp = np.hypot(u, v)
    ic = (x > 27.0) & (y > 38.38) & (y < 38.50); mid = (x > 26.6) & (x < 27.0) & (y > 38.33) & (y < 38.55); outer = x < 26.6
    lines = [f"kayıt {ds.sizes['time']} × 30 dk; dosya {len(files)}"]
    for t in range(0, ds.sizes["time"], max(1, ds.sizes["time"] // 8)):
        lines.append(f"t={(t+1)*0.5:5.1f} h  elev {np.nanmin(e[t]):+.3f}..{np.nanmax(e[t]):+.3f} m | hız maks {np.nanmax(sp[t]):.3f}; "
                     f"medyan iç {np.nanmedian(sp[t][ic]):.4f} orta {np.nanmedian(sp[t][mid]):.4f} dış {np.nanmedian(sp[t][outer]):.4f} m/s | "
                     f"n(hız>0.5)={int((sp[t]>0.5).sum())}")
    lines.append(f"kuru düğüm (son): {int(ds['dryFlagNode'].values[-1].sum())}")
    (out / "summary.txt").write_text("\n".join(lines), encoding="utf-8"); print("\n".join(lines))
    T = a.t if a.t >= 0 else ds.sizes["time"] + a.t
    tri = mtri.Triangulation(x, y, tri_from_hgrid(run / "hgrid.gr3"))
    fig, axs = plt.subplots(1, 2, figsize=(15, 6.5))
    tc = axs[0].tripcolor(tri, sp[T], vmin=0, vmax=max(0.05, float(np.nanpercentile(sp[T], 99))), cmap="viridis"); plt.colorbar(tc, ax=axs[0], label="derinlik-ort. hız (m/s)")
    axs[0].set_title(f"hız, t={(T+1)*0.5:.1f} h"); axs[0].set_aspect(1 / COSLAT)
    lim = max(0.02, float(np.nanpercentile(np.abs(e[T]), 99)))
    tc2 = axs[1].tripcolor(tri, e[T], vmin=-lim, vmax=lim, cmap="RdBu_r"); plt.colorbar(tc2, ax=axs[1], label="su seviyesi (m)")
    axs[1].set_title(f"su seviyesi, t={(T+1)*0.5:.1f} h"); axs[1].set_aspect(1 / COSLAT)
    fig.savefig(out / f"speed_elev_t{T:03d}.png", dpi=110, bbox_inches="tight")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.tripcolor(tri, sp[T], vmin=0, vmax=max(0.02, float(np.nanpercentile(sp[T][ic], 98))), cmap="Blues")
    s = ic & (np.arange(len(x)) % 20 == 0)
    ax.quiver(x[s], y[s], u[T][s], v[T][s], scale=0.6, width=0.0025, color="k")
    ax.set_xlim(27.0, 27.18); ax.set_ylim(38.38, 38.48); ax.set_aspect(1 / COSLAT); ax.set_title(f"iç körfez derinlik-ort. akım, t={(T+1)*0.5:.1f} h")
    fig.savefig(out / f"ic_korfez_t{T:03d}.png", dpi=120, bbox_inches="tight")
    # --- 3B ise: yüzey katmanı hız + T/S özeti
    f3 = sorted(glob.glob(str(run / "outputs" / "horizontalVelX_*.nc")), key=lambda f: int(Path(f).stem.split("_")[1]))
    if f3:
        def top(var):
            fs = sorted(glob.glob(str(run / "outputs" / f"{var}_*.nc")), key=lambda f: int(Path(f).stem.split("_")[1]))
            return xr.concat([xr.open_dataset(f)[var].isel(nSCHISM_vgrid_layers=-1) for f in fs], dim="time").values
        us, vs = top("horizontalVelX"), top("horizontalVelY"); ss = np.hypot(us, vs)
        l3 = [f"3B yüzey hızı: maks {np.nanmax(ss[T]):.3f} m/s; medyan iç {np.nanmedian(ss[T][ic]):.4f} orta {np.nanmedian(ss[T][mid]):.4f} dış {np.nanmedian(ss[T][outer]):.4f} (t={(T+1)*0.5:.1f} h)"]
        for var in ("temperature", "salinity"):
            if glob.glob(str(run / "outputs" / f"{var}_*.nc")):
                tv = top(var); l3.append(f"{var} yüzey (son): {np.nanmin(tv[T]):.2f}..{np.nanmax(tv[T]):.2f}, medyan {np.nanmedian(tv[T]):.2f}")
        print("\n".join(l3)); (out / "summary.txt").open("a", encoding="utf-8").write("\n" + "\n".join(l3))
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.tripcolor(tri, ss[T], vmin=0, vmax=max(0.02, float(np.nanpercentile(ss[T][ic], 98))), cmap="Blues")
        ax.quiver(x[s], y[s], us[T][s], vs[T][s], scale=0.6, width=0.0025, color="k")
        ax.set_xlim(27.0, 27.18); ax.set_ylim(38.38, 38.48); ax.set_aspect(1 / COSLAT); ax.set_title(f"iç körfez YÜZEY akımı (3B), t={(T+1)*0.5:.1f} h")
        fig.savefig(out / f"ic_korfez_yuzey_t{T:03d}.png", dpi=120, bbox_inches="tight")
    print("görseller:", out)

if __name__ == "__main__":
    main()
