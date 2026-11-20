"""Build the state-boundary asset used by the dashboard map (one-off; needs `shapely`).

Source: community dataset udit-001/india-maps-data, pinned to commit 2884453 and verified by
SHA-256. It has district polygons tagged with current state/UT names (28 states + 8 UTs,
Ladakh separate, Dadra & Nagar Haveli and Daman & Diu merged) and shows India's official
external boundary. Its README states the data was curated from public sources without
warranty; it is NOT an authoritative Survey of India product (see docs/limitations.md).

Steps: download -> verify checksum -> dissolve districts into states -> simplify ->
check the state set equals our canonical 36 names -> write dashboard/assets/india_states.geojson

    pip install shapely && python scripts/build_boundaries.py
"""
from __future__ import annotations
import hashlib, json, sys, urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.reference import REGIONS  # noqa: E402

SOURCE_URL = "https://cdn.jsdelivr.net/gh/udit-001/india-maps-data@2884453/geojson/india.geojson"
SHA256 = "e724c14bc5ee68bcdd6c"   # prefix of the verified file hash (2026-11-20)
OUT = ROOT / "dashboard" / "assets" / "india_states.geojson"
TOLERANCE = 0.015                  # degrees (~1.5 km); keeps the file small, shapes recognisable


def main() -> None:
    from shapely.geometry import shape, mapping
    from shapely.ops import unary_union

    raw = urllib.request.urlopen(SOURCE_URL, timeout=120).read()
    digest = hashlib.sha256(raw).hexdigest()
    if not digest.startswith(SHA256):
        raise SystemExit(f"checksum mismatch: {digest[:20]} != {SHA256} - refusing to build")
    src = json.loads(raw)

    parts = defaultdict(list)
    for f in src["features"]:
        parts[f["properties"]["st_nm"]].append(shape(f["geometry"]).buffer(0))

    canonical = {r.name: r for r in REGIONS}
    if set(parts) != set(canonical):
        raise SystemExit(f"state set mismatch: missing={set(canonical) - set(parts)} extra={set(parts) - set(canonical)}")

    feats = []
    for name, geoms in sorted(parts.items()):
        g = unary_union(geoms).simplify(TOLERANCE, preserve_topology=True)
        g = json.loads(json.dumps(mapping(g)), parse_float=lambda x: round(float(x), 4))
        r = canonical[name]
        feats.append({"type": "Feature", "id": r.code,
                      "properties": {"state": name, "code": r.code, "kind": r.kind}, "geometry": g})
    out = {"type": "FeatureCollection",
           "metadata": {"source": SOURCE_URL, "sha256_prefix": SHA256, "processing": f"districts dissolved to states, simplified {TOLERANCE} deg",
                        "caveat": "Community dataset, not an authoritative Survey of India product."},
           "features": feats}
    OUT.write_text(json.dumps(out, separators=(",", ":")))
    print(f"wrote {OUT} ({OUT.stat().st_size/1e6:.2f} MB, {len(feats)} features)")


if __name__ == "__main__":
    main()
