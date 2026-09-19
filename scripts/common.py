"""Ortak yardımcılar: yollar, config okuma."""
from __future__ import annotations
import csv, json, os
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config"
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
RUNS = ROOT / "runs"

def params() -> dict:
    return yaml.safe_load((CFG / "model_params.yaml").read_text(encoding="utf-8"))

def domain(feature_id: str) -> dict:
    d = json.loads((CFG / "domain.geojson").read_text(encoding="utf-8"))
    for ft in d["features"]:
        if ft["properties"]["id"] == feature_id:
            return ft
    raise KeyError(feature_id)

def bbox(feature_id: str) -> tuple[float, float, float, float]:
    """(lon_min, lon_max, lat_min, lat_max)"""
    p = domain(feature_id)["properties"]
    return p["lon_min"], p["lon_max"], p["lat_min"], p["lat_max"]

def point(feature_id: str) -> tuple[float, float]:
    """(lon, lat) — Point geometrili alan öğesi"""
    return tuple(domain(feature_id)["geometry"]["coordinates"])

def sources() -> list[dict]:
    with open(CFG / "sources.csv", encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if r["lon"] and r["lat"]]

def load_env() -> None:
    """Depo kökündeki .env dosyasını os.environ'a yükler (cdsapi ve copernicusmarine env değişkenlerini okur)."""
    f = ROOT / ".env"
    if not f.exists():
        return
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
