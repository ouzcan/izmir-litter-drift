"""Ortam kontrolü: paketler, kimlik dosyaları, config dosyaları."""
from __future__ import annotations
import importlib, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def check_pkgs():
    ok = True
    for name in ["numpy", "xarray", "netCDF4", "pandas", "geopandas", "shapely",
                 "matplotlib", "copernicusmarine", "cdsapi", "opendrift"]:
        try:
            m = importlib.import_module(name)
            print(f"  [ok] {name} {getattr(m, '__version__', '')}")
        except Exception as e:  # noqa: BLE001
            ok = False
            print(f"  [--] {name}: {e.__class__.__name__}")
    return ok

def check_creds():
    home = Path.home()
    cm = home / ".copernicusmarine"
    cds = home / ".cdsapirc"
    print(f"  [{'ok' if cm.exists() else '--'}] Copernicus Marine girişi ({cm})")
    print(f"  [{'ok' if cds.exists() else '--'}] CDS anahtarı ({cds})")
    return cm.exists() and cds.exists()

def check_config():
    ok = True
    for f in ["config/domain.geojson", "config/sources.csv",
              "config/coast_zones.csv", "config/model_params.yaml"]:
        p = ROOT / f
        exists = p.exists()
        ok &= exists
        print(f"  [{'ok' if exists else '--'}] {f}")
    dom = json.loads((ROOT / "config/domain.geojson").read_text(encoding="utf-8"))
    for ft in dom["features"]:
        print(f"      alan: {ft['properties']['id']}")
    import csv
    with open(ROOT / "config/sources.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    missing = [r["id"] for r in rows if not r["lon"] or not r["lat"]]
    unverified = [r["id"] for r in rows if r["verified"] != "yes"]
    print(f"      kaynak: {len(rows)} nokta, koordinatsız {len(missing)} {missing}, doğrulanmamış {len(unverified)}")
    return ok

if __name__ == "__main__":
    print("Paketler:");  a = check_pkgs()
    print("Kimlik:");    b = check_creds()
    print("Config:");    c = check_config()
    sys.exit(0 if (a and c) else 1)
