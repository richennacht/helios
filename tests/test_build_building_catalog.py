import json
import sqlite3

from scripts.ingestion.build_building_catalog import (
    create_schema,
    ingest,
    query_fused,
    stream_geojson_features,
)


def _feature(source_id, west, south, east, north, height=None):
    return {
        "type": "Feature",
        "properties": {"source_record_id": source_id, "height_m": height},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[west, south], [east, south], [east, north], [west, north], [west, south]]],
        },
    }


def test_streaming_reader_and_fused_height(tmp_path):
    source = tmp_path / "source.geojson"
    source.write_text(
        json.dumps({"type": "FeatureCollection", "metadata": {}, "features": [_feature("g1", 72.9, 19.0, 72.9001, 19.0001)]}),
        encoding="utf-8",
    )
    assert len(list(stream_geojson_features(source, chunk_size=19))) == 1

    connection = sqlite3.connect(":memory:")
    create_schema(connection)
    ingest(connection, "google-open-buildings-v3", [_feature("g1", 72.9, 19.0, 72.9001, 19.0001)])
    ingest(connection, "microsoft-global-ml-buildings-2026-08-13", [_feature("m1", 72.9, 19.0, 72.9001, 19.0001, 20)])
    overture = _feature("o1", 72.9, 19.0, 72.9001, 19.0001)
    overture.update({"id": "o1", "height": 30, "sources": [{"dataset": "OpenStreetMap"}]})
    ingest(connection, "overture-buildings-2026-07-22", [overture])
    result = query_fused(connection, (72.89, 18.99, 72.91, 19.01))
    assert result["metadata"]["building_count"] == 1
    assert result["features"][0]["properties"]["height_m"] == 25.0
    assert result["features"][0]["properties"]["synthetic_height"] is False


def test_missing_height_stays_null():
    connection = sqlite3.connect(":memory:")
    create_schema(connection)
    ingest(connection, "google-open-buildings-v3", [_feature("g1", 72.9, 19.0, 72.9001, 19.0001)])
    result = query_fused(connection, (72.89, 18.99, 72.91, 19.01))
    assert result["features"][0]["properties"]["height_m"] is None
