"""OpenDrift sonuçlarını toplulaştırma (41/42/43 ortak): kıyı bölgesi ataması, matris, geojson, görsel.

Bölge ataması: config/coast_zones.csv'deki kutular SIRAYLA denenir (ilk eşleşen kazanır; adalar büyük kutulardan önce).
Kıyıya vuran ama hiçbir kutuya girmeyen nokta: model alanı (B_model) içindeyse "Z00 tanımsız kıyı" (uyarı basılır —
kutu eksik demektir), dışındaysa "Z12 alan dışı". Denizde kalanlar da Z12 sayılır (bağlantı matrisinde "ulaşmadı").
"""
from __future__ import annotations
import csv, json
from pathlib import Path
import numpy as np

from common import CFG, bbox

COSLAT = np.cos(np.deg2rad(38.5))
Z00 = ("Z00", "tanımsız kıyı (kutu eksik)")

def zones():
    rows = list(csv.DictReader(open(CFG / "coast_zones.csv", encoding="utf-8")))
    def fl(v):
        try: return float(v)
        except (TypeError, ValueError): return None
    return [(r["zone_id"], r["name"], *(fl(r.get(k)) for k in ("lon_min", "lon_max", "lat_min", "lat_max"))) for r in rows]

def zone_of(lon, lat, Z, dom=None):
    for zid, name, x0, x1, y0, y1 in Z:
        if x0 is None: continue
        if x0 <= lon <= x1 and y0 <= lat <= y1: return zid, name
    if dom is not None and dom[0] <= lon <= dom[1] and dom[2] <= lat <= dom[3]: return Z00
    return "Z12", "Körfez dışı / açık Ege"

def zone_names(Z):
    d = {z[0]: z[1] for z in Z}; d[Z00[0]] = Z00[1]; return d

def assign_zones(lon, lat, stranded):
    """Dizi halinde bölge kimliği; denizde kalanlar Z12."""
    Z = zones(); dom = bbox("B_model")
    out = np.array([zone_of(x, y, Z, dom)[0] if (np.isfinite(x) and s) else ("Z12" if np.isfinite(x) else "NA")
                    for x, y, s in zip(lon, lat, stranded)], dtype=object)
    n00 = int((out == "Z00").sum())
    if n00: print(f"[agg] uyarı: {n00} parçacık alan içinde ama hiçbir kıyı kutusuna girmiyor (Z00) — coast_zones.csv'ye kutu ekle")
    return out, Z

def aggregate(out: Path, origins: list[dict], endpoints: dict, meta: dict):
    """origins: [{origin, name, lon, lat}], endpoints: dict of arrays (origin_idx, lon, lat, stranded, t_rel, t_end).
    Yazar: endpoints.csv, matrix.csv, summary.txt, (grid) cells.geojson; döner rows, zone dizisi."""
    om = endpoints["origin_idx"]; lon = endpoints["lon"]; lat = endpoints["lat"]
    stranded = endpoints["stranded"].astype(bool); t_rel = endpoints["t_rel"]; t_end = endpoints["t_end"]
    zone, Z = assign_zones(lon, lat, stranded); zn = zone_names(Z)
    zids = [z[0] for z in Z if z[0] != "Z12"] + ["Z00", "Z12"]
    ids = [o["origin"] for o in origins]
    with open(out / "endpoints.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh); w.writerow(["origin", "lon_end", "lat_end", "stranded", "t_release_h", "t_end_h", "zone_id"])
        for i in range(len(lon)):
            if np.isfinite(lon[i]): w.writerow([ids[om[i]], f"{lon[i]:.5f}", f"{lat[i]:.5f}", int(stranded[i]), f"{t_rel[i]:.0f}", f"{t_end[i]:.1f}", zone[i]])
    rows = []
    for k, o in enumerate(origins):
        m = om == k; n = int(m.sum())
        if n == 0: continue
        r = {"origin": o["origin"], "name": o["name"], "lon": f"{float(o['lon']):.4f}", "lat": f"{float(o['lat']):.4f}", "n": n,
             "stranded_frac": f"{stranded[m].mean():.3f}",
             "t_strand_med_h": f"{np.median((t_end - t_rel)[m & stranded]):.1f}" if (m & stranded).any() else ""}
        for z in zids: r[z] = f"{((zone == z) & m).sum() / n:.3f}"
        dom = max([z for z in zids if z not in ("Z12", "Z00")] + ["Z12"], key=lambda z: float(r[z]))
        r["dominant"] = dom; r["dominant_frac"] = r[dom]
        rows.append(r)
    with open(out / "matrix.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    hdr = meta.get("header", "")
    lines = [hdr, (f"kıyıya vuran toplam: %{100*stranded.mean():.0f}; medyan vurma süresi {np.median((t_end-t_rel)[stranded]):.1f} h"
                   if stranded.any() else "kıyıya vuran yok"), ""]
    tot = {z: float(np.mean([float(r[z]) for r in rows])) for z in zids}
    lines.append("bölge payları (salım noktalarının DÜZ ortalaması — kaynak yükü ağırlıklı için 53_weighted_shares.py): " + ", ".join(f"{z} %{100*tot[z]:.0f}" for z in zids if tot[z] >= 0.005))
    if meta.get("mode") == "sources":
        lines += ["", f"{'kaynak':6s} {'ad':28s} {'vuran':>6s} {'süre':>6s}  baskın bölge"]
        for r in rows: lines.append(f"{r['origin']:6s} {r['name'][:28]:28s} {100*float(r['stranded_frac']):5.0f}% {r['t_strand_med_h']:>6s}  {r['dominant']} {zn.get(r['dominant'],'')} %{100*float(r['dominant_frac']):.0f}")
    else:
        feats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [float(r["lon"]), float(r["lat"])]},
                  "properties": {k: (float(v) if k not in ("origin", "name", "dominant") and v != "" else v) for k, v in r.items()}} for r in rows]
        json.dump({"type": "FeatureCollection", **{k: meta[k] for k in ("cell_km", "run", "start", "days") if k in meta},
                   "zones": zn, "features": feats}, open(out / "cells.geojson", "w", encoding="utf-8"), ensure_ascii=False)
    (out / "summary.txt").write_text("\n".join(lines), encoding="utf-8"); print("\n".join(lines))
    return rows, zone, zn

def mesh_coast(f: Path):
    """Ağ sınır kenarları (yalnız bir üçgene ait kenarlar) → kıyı çizgisi parçaları."""
    import xarray as xr
    d = xr.open_dataset(f, decode_times=False)
    x = d.SCHISM_hgrid_node_x.values; y = d.SCHISM_hgrid_node_y.values
    tri = d.SCHISM_hgrid_face_nodes.values.astype(int) - 1
    e = np.vstack([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]]); e.sort(axis=1)
    u, c = np.unique(e, axis=0, return_counts=True); b = u[c == 1]
    return [((x[i], y[i]), (x[j], y[j])) for i, j in b]

def plot_matrix(out: Path, origins, endpoints, rows, zn, meta, coast_file=None):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    x0, x1, y0, y1 = bbox("B_model")
    om = endpoints["origin_idx"]; lon = endpoints["lon"]; lat = endpoints["lat"]; stranded = endpoints["stranded"].astype(bool)
    fig, ax = plt.subplots(figsize=(11, 8))
    if coast_file and Path(coast_file).exists():
        ax.add_collection(LineCollection(mesh_coast(Path(coast_file)), colors="0.35", linewidths=0.5, zorder=1))
    title = f"{meta.get('run','')}, {meta.get('start','')} +{meta.get('days','')} g, windage %{100*float(meta.get('windage', 0.02)):.0f}"
    if meta.get("mode") == "sources":
        cmap = plt.get_cmap("tab20", len(origins))
        for k, o in enumerate(origins):
            m = (om == k) & stranded
            if m.any(): ax.scatter(lon[m], lat[m], s=6, color=cmap(k), alpha=0.7)
            ax.plot(float(o["lon"]), float(o["lat"]), "k^", ms=8); ax.annotate(o["origin"], (float(o["lon"]), float(o["lat"])), fontsize=8, xytext=(3, 3), textcoords="offset points")
        act = ~stranded & np.isfinite(lon)
        if act.any(): ax.scatter(lon[act], lat[act], s=4, color="0.5", alpha=0.5)
        ax.set_title("kaynaklardan kıyıya vuranlar — " + title)
    else:
        cell_km = float(meta.get("cell_km", 1.0))
        zl = sorted(set(r["dominant"] for r in rows)); cm = plt.get_cmap("tab20", max(len(zl), 1))
        for j, z in enumerate(zl):
            rr = [r for r in rows if r["dominant"] == z]
            ax.scatter([float(r["lon"]) for r in rr], [float(r["lat"]) for r in rr], s=(cell_km * 9) ** 2, marker="s", color=cm(j), label=f"{z} {zn.get(z,'')}")
        ax.legend(fontsize=7, loc="upper left"); ax.set_title("hücre → baskın varış bölgesi — " + title)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect(1 / COSLAT); ax.grid(alpha=0.3)
    fig.savefig(out / "matrix.png", dpi=120, bbox_inches="tight"); plt.close(fig)

def endpoints_from_result(ds):
    """OpenDrift o.result → endpoints sözlüğü (origin_idx, lon, lat, stranded, t_rel, t_end)."""
    omv = ds["origin_marker"].values
    om = (np.nanmax(omv, axis=1) if omv.ndim == 2 else omv)
    om = np.where(np.isfinite(om), om, 0).astype(int)
    lon = ds["lon"].ffill("time").isel(time=-1).values; lat = ds["lat"].ffill("time").isel(time=-1).values
    stat = ds["status"].values.astype(float); fm = ds["status"].attrs.get("flag_meanings", "").split(); meaning = {i: n for i, n in enumerate(fm)}
    last = np.array([r[np.isfinite(r)][-1] if np.isfinite(r).any() else np.nan for r in stat])
    stranded = np.array([meaning.get(int(v), "?") == "stranded" if np.isfinite(v) else False for v in last])
    tv = ds["time"].values; hours = (tv - tv[0]) / np.timedelta64(1, "h")
    t_end = np.array([hours[np.where(np.isfinite(r))[0][-1]] if np.isfinite(r).any() else np.nan for r in stat])
    t_rel = np.array([hours[np.where(np.isfinite(r))[0][0]] if np.isfinite(r).any() else np.nan for r in stat])
    return {"origin_idx": om, "lon": lon, "lat": lat, "stranded": stranded, "t_rel": t_rel, "t_end": t_end}

def endpoints_from_csv(p: Path, origins):
    idx = {o["origin"]: k for k, o in enumerate(origins)}
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    return {"origin_idx": np.array([idx[r["origin"]] for r in rows]),
            "lon": np.array([float(r["lon_end"]) for r in rows]), "lat": np.array([float(r["lat_end"]) for r in rows]),
            "stranded": np.array([r["stranded"] == "1" for r in rows]),
            "t_rel": np.array([float(r["t_release_h"]) for r in rows]), "t_end": np.array([float(r["t_end_h"]) for r in rows])}
