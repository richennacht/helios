from scripts.ingestion.clip_public_buildings import parse_polygon_wkt, write_collection


def test_parses_google_polygon_and_multipolygon():
    polygon = parse_polygon_wkt("POLYGON((72 19,73 19,73 20,72 19))")
    multi = parse_polygon_wkt(
        "MULTIPOLYGON(((72 19,73 19,72 19)), ((74 19,75 19,74 19)))"
    )
    assert polygon["type"] == "Polygon"
    assert len(multi["coordinates"]) == 2


def test_collection_writer_streams_valid_geojson(tmp_path):
    destination = tmp_path / "buildings.geojson"
    count = write_collection(
        ({"type": "Feature", "properties": {"id": index}, "geometry": None} for index in range(3)),
        destination,
        {"source": "test"},
    )
    assert count == 3
    assert '"id":2' in destination.read_text(encoding="utf-8")
