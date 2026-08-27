import hashlib
import json
from pathlib import Path

from helios.contracts.models import SourceManifest
from helios.ingestion.identity import candidate_id, source_record_digest

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "sample" / "source_layers"


def test_candidate_identity_is_independent_of_row_order() -> None:
    wkt = "POLYGON((73 19, 73.1 19, 73.1 19.1, 73 19))"
    first = candidate_id("3bf", "7J...", wkt)
    second = candidate_id("3bf", "7J...", "  POLYGON((73 19, 73.1 19, 73.1 19.1, 73 19))  ")
    assert first == second
    digest = source_record_digest("3bf", "7J...", wkt)
    assert digest in f"gobv3:3bf:sha256:{digest}"


def test_fixture_is_real_source_handoff_without_downstream_fields() -> None:
    data = json.loads((SOURCE_DIR / "candidate_buildings.geojson").read_text(encoding="utf-8"))
    assert 10 <= len(data["features"]) <= 20
    ids = [feature["properties"]["candidate_id"] for feature in data["features"]]
    assert len(ids) == len(set(ids))
    forbidden = {
        "usable_roof_area_m2",
        "estimated_capacity_kwp",
        "annual_yield_kwh",
        "capex_inr",
        "rent_inr_month",
        "payback_years",
        "rank",
        "score",
    }
    for feature in data["features"]:
        props = feature["properties"]
        assert props["source_dataset"] == "Google Open Buildings"
        assert props["source_version"] == "v3"
        assert props["source_record_key"].startswith("gobv3:3bf:sha256:")
        assert forbidden.isdisjoint(props)


def test_source_manifest_records_match_contract() -> None:
    path = ROOT / "data" / "manifests" / "source_manifest.json"
    records = json.loads(path.read_text(encoding="utf-8"))
    assert len(records) >= 5
    for record in records:
        SourceManifest.model_validate(record)


def test_geolibre_sources_resolve_inside_checkout() -> None:
    project_path = ROOT / "apps" / "geolibre" / "base_project" / "kharghar_helios_base.json"
    project = json.loads(project_path.read_text(encoding="utf-8"))
    assert {layer["id"] for layer in project["layers"]} == {
        "aoi_boundary",
        "buildings",
        "power",
        "roads",
        "terrain",
    }
    for layer in project["layers"]:
        assert not Path(layer["source"]).is_absolute()
        assert (project_path.parent / layer["source"]).resolve().is_file()
        assert layer["attribution"]


def test_committed_checksums_match() -> None:
    checksums = json.loads(
        (ROOT / "data" / "manifests" / "checksums.sha256.json").read_text(encoding="utf-8")
    )
    for relative_path, expected in checksums.items():
        payload = (ROOT / relative_path).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == expected
