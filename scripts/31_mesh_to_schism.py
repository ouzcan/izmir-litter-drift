"""meshkernel/UGRID ağı (izmir_net.nc) → SCHISM hgrid.gr3 (+ hgrid.ll), derinlikler EMODnet'ten yeniden.

Yapılanlar
- Derinlik: EMODnet'ten doğrusal interpolasyon; kıyıda NaN kalan düğümler en yakın geçerli DENİZ
  hücresinden (≤ max_fill_dist_m) doldurulur; daha uzak düğümlerden oluşan hücreler (tuzla, lagün,
  kara artıkları) ağdan atılır; en az derinlik min_depth_m.
- Bağlantısız ada parçaları (ana su kütlesine bağlı olmayan hücre grupları) atılır.
- Elemanlar saat yönünün tersine sıralanır; üçgen/dörtgen karma ağ desteklenir.
- Sınır: dış çevre döngüsü CCW, adalar CW. Kutu kenarlarına (open_edges) oturan çevre düğümleri
  açık sınır; kısa parçalar (< min_open_nodes düğüm) kara sayılır.

Kullanım:
    python scripts/31_mesh_to_schism.py [--net runs/dflowfm/izmir_2D/izmir_net.nc] [--out runs/schism/izmir]
Çıktı: hgrid.gr3, hgrid.ll, boundary_summary.txt, hgrid_check.png
"""
from __future__ import annotations
import argparse
from pathlib import Path

import numpy as np
import xarray as xr

from common import ROOT, RAW, RUNS, bbox, params

P = params(); D = P.get("dflowfm", {}); S = P.get("schism", {})
COSLAT = np.cos(np.deg2rad(38.6))

def log(*a): print("[31]", *a, flush=True)

# ----------------------------------------------------------------------------- derinlik
def node_depths(x, y):
    from scipy.spatial import cKDTree
    f = RAW / "bathy" / "emodnet_dtm2024_A.nc"
    da = xr.open_dataset(f)["elevation"].rename({"latitude": "lat", "longitude": "lon"})
    if da.lat[0] > da.lat[-1]: da = da.sortby("lat")
    da = da.sel(lon=slice(x.min() - 0.05, x.max() + 0.05), lat=slice(y.min() - 0.05, y.max() + 0.05)).load()
    z = da.interp(lon=xr.DataArray(x, dims="n"), lat=xr.DataArray(y, dims="n")).values.astype(float)
    nan = np.isnan(z)
    LON, LAT = np.meshgrid(da.lon.values, da.lat.values)
    sea = np.isfinite(da.values) & (da.values < 0)
    tree = cKDTree(np.c_[LON[sea] * COSLAT, LAT[sea]])
    dist, idx = tree.query(np.c_[x[nan] * COSLAT, y[nan]])
    dist_m = dist * 111_000
    maxd = float(S.get("max_fill_dist_m", 600))
    zfill = da.values[sea][idx]
    z[nan] = zfill
    far = np.zeros_like(nan); far[np.where(nan)[0][dist_m > maxd]] = True
    log(f"derinlik: {nan.sum()} kıyı düğümü en yakın deniz hücresinden dolduruldu (medyan {np.median(dist_m):.0f} m); "
        f"{far.sum()} düğüm {maxd:.0f} m'den uzak (kara/tuzla adayı)")
    return z, far

# ----------------------------------------------------------------------------- topoloji yardımcıları
def face_node_list(g):
    fn = g.face_node_connectivity
    fill = g.fill_value
    return [row[row != fill] for row in fn]

def signed_area(xs, ys):
    return 0.5 * np.sum(xs * np.roll(ys, -1) - np.roll(xs, -1) * ys)

def boundary_loops(faces, nnode):
    """Sınır kenarlarını (tek yüze ait) döngülere zincirler. Her döngü düğüm listesi (kapalı değil)."""
    from collections import defaultdict
    cnt = defaultdict(int); edge_dir = {}
    for f in faces:
        n = len(f)
        for i in range(n):
            a, b = int(f[i]), int(f[(i + 1) % n])
            key = (min(a, b), max(a, b)); cnt[key] += 1; edge_dir[key] = (a, b)
    bedges = [edge_dir[k] for k, c in cnt.items() if c == 1]   # yüz CCW ise sınır kenarı (a->b) su solda
    nxt = defaultdict(list)
    for a, b in bedges: nxt[a].append(b)
    used = set(); loops = []
    for a, b in bedges:
        if (a, b) in used: continue
        loop = [a]; cur, prev = b, a; used.add((a, b))
        while cur != a:
            loop.append(cur)
            cands = [c for c in nxt[cur] if (cur, c) not in used]
            if not cands: break
            c = cands[0]; used.add((cur, c)); prev, cur = cur, c
        loops.append(loop)
    return loops

# ----------------------------------------------------------------------------- ana
def main():
    import xugrid as xu
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    ap = argparse.ArgumentParser()
    ap.add_argument("--net", default=str(RUNS / "dflowfm" / "izmir_2D" / "izmir_net.nc"))
    ap.add_argument("--out", default=str(RUNS / "schism" / S.get("run_name", "izmir")))
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    uds = xu.open_dataset(a.net); g = uds.grid
    x, y = g.node_x.copy(), g.node_y.copy()
    faces = face_node_list(g)
    log(f"girdi: {len(x)} düğüm, {len(faces)} yüz ({sum(len(f)==3 for f in faces)} üçgen, {sum(len(f)==4 for f in faces)} dörtgen)")

    z, far = node_depths(x, y)
    # 1) tüm düğümleri 'uzak' olan yüzleri at
    keep = np.array([not far[f].all() for f in faces])
    log(f"kara/tuzla artığı olarak atılan yüz: {(~keep).sum()}")
    faces = [f for f, k in zip(faces, keep) if k]
    # 2) bağlı bileşenler: en büyük su kütlesini tut
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    rows, cols = [], []
    for f in faces:
        for i in range(len(f)):
            rows.append(f[i]); cols.append(f[(i + 1) % len(f)])
    A = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(x), len(x)))
    ncomp, lab = connected_components(A, directed=False)
    face_lab = np.array([lab[f[0]] for f in faces])
    big = np.bincount(face_lab, minlength=ncomp).argmax()
    log(f"bağlı bileşen: {ncomp}; ana kütle dışında atılan yüz: {(face_lab != big).sum()}")
    faces = [f for f, l in zip(faces, face_lab) if l == big]
    # 2b) "kıstırma" düğümleri: sınır kenar grafiğinde derecesi 2'den büyük düğüm (iki su kütlesi tek düğümde
    #     değiyor / papyon). SCHISM bunu kabul etmez; düğüme değen en küçük yüzü at, tekrarla.
    from collections import defaultdict
    def pinch_nodes(faces):
        cnt = defaultdict(int)
        for f in faces:
            n = len(f)
            for i in range(n):
                a, b = int(f[i]), int(f[(i + 1) % n]); cnt[(min(a, b), max(a, b))] += 1
        deg = defaultdict(int)
        for (a, b), c in cnt.items():
            if c == 1: deg[a] += 1; deg[b] += 1
        return [n for n, d in deg.items() if d > 2]
    def face_area(f): return abs(signed_area(x[f] * COSLAT, y[f]))
    for it in range(20):
        pn = pinch_nodes(faces)
        if not pn: break
        drop = set()
        for n in pn:
            adj = [i for i, f in enumerate(faces) if n in f]
            drop.add(min(adj, key=lambda i: face_area(faces[i])))
        faces = [f for i, f in enumerate(faces) if i not in drop]
        log(f"kıstırma düğümü: {len(pn)} -> {len(drop)} yüz atıldı (tur {it+1})")
    # kıstırma temizliği parça koparmış olabilir: bileşenleri yeniden hesapla
    rows, cols = [], []
    for f in faces:
        for i in range(len(f)):
            rows.append(f[i]); cols.append(f[(i + 1) % len(f)])
    A = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(x), len(x)))
    ncomp, lab = connected_components(A, directed=False)
    face_lab = np.array([lab[f[0]] for f in faces]); big = np.bincount(face_lab, minlength=ncomp).argmax()
    if (face_lab != big).any(): log(f"kıstırma sonrası kopan yüz: {(face_lab != big).sum()} atıldı")
    faces = [f for f, l in zip(faces, face_lab) if l == big]
    # 3) kullanılmayan düğümleri temizle, yeniden numaralandır
    used = np.unique(np.concatenate(faces)); remap = -np.ones(len(x), int); remap[used] = np.arange(len(used))
    x, y, z = x[used], y[used], z[used]
    faces = [remap[f] for f in faces]
    # 4) CCW ve derinlik işareti (SCHISM: pozitif aşağı), min derinlik
    for i, f in enumerate(faces):
        if signed_area(x[f], y[f]) < 0: faces[i] = f[::-1]
    mind = float(S.get("min_depth_m", 1.0))
    dep = np.maximum(-z, mind)
    log(f"çıktı: {len(x)} düğüm, {len(faces)} yüz; derinlik {dep.min():.1f}–{dep.max():.1f} m, medyan {np.median(dep):.1f}")

    # 5) sınırlar
    loops = boundary_loops(faces, len(x))
    areas = [signed_area(x[l], y[l]) for l in loops]
    outer_i = int(np.argmax(np.abs(areas)))
    outer = loops[outer_i]
    if areas[outer_i] < 0: outer = outer[::-1]                       # dış çevre CCW
    islands = [l if signed_area(x[l], y[l]) < 0 else l[::-1] for j, l in enumerate(loops) if j != outer_i]  # adalar CW
    # açık sınır: kutu kenarlarındaki düğümler
    lon0, lon1, lat0, lat1 = bbox(D.get("domain_id", "B_model"))
    tol = 2e-3
    allowed = set(D.get("open_edges", ["north", "west"]))
    on_edge = np.zeros(len(x), bool)
    if "west" in allowed:  on_edge |= np.abs(x - x.min()) < tol
    if "north" in allowed: on_edge |= np.abs(y - y.max()) < tol
    if "east" in allowed:  on_edge |= np.abs(x - x.max()) < tol
    if "south" in allowed: on_edge |= np.abs(y - y.min()) < tol
    # sığ kıyı kesimleri açık sınır olmasın (sınır jetleri): derinlik < min_open_depth_m → kara
    min_od = float(S.get("min_open_depth_m", 30.0))
    on_edge &= dep >= min_od
    is_open = on_edge[np.array(outer)].copy()
    N = len(outer)
    # döngüyü bir kara düğümünden başlat
    if not is_open.all():
        st = int(np.argmin(is_open)); outer = outer[st:] + outer[:st]; is_open = np.roll(is_open, -st)
    # ardışık koşular (run-length)
    runs = []  # (open?, [indeksler])
    for k in range(N):
        if runs and runs[-1][0] == bool(is_open[k]): runs[-1][1].append(k)
        else: runs.append([bool(is_open[k]), [k]])
    min_open = int(S.get("min_open_nodes", 6))
    for r in runs:                       # kısa açık koşular kara olur
        if r[0] and len(r[1]) < min_open: r[0] = False
    merged = []
    for r in runs:                       # bitişik aynı tür koşuları birleştir
        if merged and merged[-1][0] == r[0]: merged[-1][1].extend(r[1])
        else: merged.append([r[0], list(r[1])])
    if len(merged) > 1 and merged[0][0] == merged[-1][0]:   # döngü kapanışında birleştir
        merged[0][1] = merged[-1][1] + merged[0][1]; merged.pop()
    open_segs, land_segs = [], []
    M = len(merged)
    for i, (op, idx) in enumerate(merged):
        nodes = [outer[k] for k in idx]
        if op:
            open_segs.append(nodes)
        else:
            # kara parçası komşu açık parçaların uç düğümlerini de içerir (SCHISM kuralı)
            prev_last = outer[merged[i - 1][1][-1]] if M > 1 else None
            next_first = outer[merged[(i + 1) % M][1][0]] if M > 1 else None
            seg = ([prev_last] if prev_last is not None else []) + nodes + ([next_first] if next_first is not None else [])
            land_segs.append(seg)
    log(f"sınır: dış çevre {N} düğüm; açık sınır {len(open_segs)} parça ({sum(len(s) for s in open_segs)} düğüm); "
        f"kara {len(land_segs)} parça; ada {len(islands)}")
    # 6) hgrid.gr3 yaz
    def write(path):
        with open(path, "w") as fh:
            fh.write("izmir korfezi — meshkernel agi, EMODnet DTM2024 derinlik (LAT), lon/lat\n")
            fh.write(f"{len(faces)} {len(x)}\n")
            for i in range(len(x)):
                fh.write(f"{i+1} {x[i]:.7f} {y[i]:.7f} {dep[i]:.3f}\n")
            for i, f in enumerate(faces):
                fh.write(f"{i+1} {len(f)} " + " ".join(str(int(n) + 1) for n in f) + "\n")
            fh.write(f"{len(open_segs)} = Number of open boundaries\n")
            fh.write(f"{sum(len(s) for s in open_segs)} = Total number of open boundary nodes\n")
            for j, s in enumerate(open_segs):
                fh.write(f"{len(s)} = Number of nodes for open boundary {j+1}\n")
                fh.writelines(f"{int(n)+1}\n" for n in s)
            nland = len(land_segs) + len(islands)
            fh.write(f"{nland} = Number of land boundaries\n")
            fh.write(f"{sum(len(s) for s in land_segs) + sum(len(l)+1 for l in islands)} = Total number of land boundary nodes\n")
            for j, s in enumerate(land_segs):
                fh.write(f"{len(s)} 0 = Number of nodes for land boundary {j+1}\n")
                fh.writelines(f"{int(n)+1}\n" for n in s)
            for j, l in enumerate(islands):
                fh.write(f"{len(l)+1} 1 = Number of nodes for island boundary {j+1}\n")
                fh.writelines(f"{int(n)+1}\n" for n in list(l) + [l[0]])
    write(out / "hgrid.gr3"); write(out / "hgrid.ll")
    (out / "boundary_summary.txt").write_text(
        "\n".join([f"open {j+1}: {len(s)} node, lon {x[s].min():.3f}-{x[s].max():.3f}, lat {y[s].min():.3f}-{y[s].max():.3f}" for j, s in enumerate(open_segs)]
                  + [f"land segs: {len(land_segs)}", f"islands: {len(islands)}"]), encoding="utf-8")
    log("yazıldı:", out / "hgrid.gr3")

    # 7) görsel
    fig, ax = plt.subplots(figsize=(10, 8))
    import matplotlib.tri as mtri
    tris = []
    for f in faces:
        f = list(f)
        tris.append([f[0], f[1], f[2]])
        if len(f) == 4: tris.append([f[0], f[2], f[3]])
    tri = mtri.Triangulation(x, y, np.array(tris))
    tc = ax.tripcolor(tri, dep, vmin=0, vmax=80, cmap="Blues"); plt.colorbar(tc, ax=ax, label="derinlik (m)")
    for s in open_segs: ax.plot(x[s], y[s], "r-", lw=2.5)
    ax.set_aspect(1 / COSLAT); ax.set_title(f"hgrid: {len(x)} düğüm, {len(faces)} eleman; kırmızı = açık sınır ({len(open_segs)})")
    fig.savefig(out / "hgrid_check.png", dpi=130, bbox_inches="tight")
    ax.set_xlim(27.0, 27.2); ax.set_ylim(38.38, 38.50); tc.set_clim(0, 20); ax.set_title("iç körfez derinlik (m)")
    fig.savefig(out / "hgrid_ic_korfez.png", dpi=130, bbox_inches="tight")
    log("görseller:", out / "hgrid_check.png")

if __name__ == "__main__":
    main()
