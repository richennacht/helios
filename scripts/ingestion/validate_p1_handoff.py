"""Validate the checked-in Person 1 handoff without network access."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from helios.contracts.models import SourceManifest

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "data" / "sample" / "source_layers"
FORBIDDEN_FIELDS = {
    "usable_roof_area_m2",
    "estimated_capacity_kwp",
    "annual_yield_kwh",
    "capex_inr",
    "rent_inr_month",
    "payback_years",
    "score",
    "rank",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    fixture_path = SOURCE_DIR / "candidate_buildings.geojson"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    features = fixture["features"]
    if not 10 <= len(features) <= 20:
        raise ValueError("Person 1 fixture must contain 10-20 candidates")

    ids: list[str] = []
    for feature in features:
        props = feature["properties"]
        ids.append(props["candidate_id"])
        if FORBIDDEN_FIELDS.intersection(props):
            raise ValueError(f"Downstream fields found on {props['candidate_id']}")
        if props["source_dataset"] != "Google Open Buildings" or props["source_version"] != "v3":
            raise ValueError("Candidate source identity is not Google Open Buildings v3")
        if not props["source_record_key"].startswith("gobv3:3bf:sha256:"):
            raise ValueError("Source surrogate key is missing its explicit derivation")
        height = props["temporal_height_m"]
        presence = props["temporal_presence_score"]
        if height is not None and not 0 < height <= 100:
            raise ValueError("Temporal height is outside the documented range")
        if presence is not None and not 0 <= presence <= 1:
            raise ValueError("Temporal presence score is outside [0, 1]")
    if len(ids) != len(set(ids)):
        raise ValueError("candidate_id values are not unique")

    manifests = json.loads(
        (ROOT / "data" / "manifests" / "source_manifest.json").read_text(encoding="utf-8")
    )
    for record in manifests:
        SourceManifest.model_validate(record)

    checksums = json.loads(
        (ROOT / "data" / "manifests" / "checksums.sha256.json").read_text(encoding="utf-8")
    )
    for relative_path, expected in checksums.items():
        path = ROOT / relative_path
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"Checksum mismatch: {relative_path}")

    project_path = ROOT / "apps" / "geolibre" / "base_project" / "kharghar_helios_base.json"
    project = json.loads(project_path.read_text(encoding="utf-8"))
    for layer in project["layers"]:
        source = (project_path.parent / layer["source"]).resolve()
        if not source.is_file():
            raise ValueError(f"GeoLibre layer path is not portable: {layer['source']}")
        if not layer.get("attribution"):
            raise ValueError(f"GeoLibre layer lacks attribution: {layer['id']}")

    observed_heights = sum(
        feature["properties"]["temporal_height_m"] is not None for feature in features
    )
    print(
        json.dumps(
            {
                "status": "pass",
                "candidate_count": len(features),
                "temporal_height_observations": observed_heights,
                "manifest_records": len(manifests),
                "geolibre_layers": len(project["layers"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
