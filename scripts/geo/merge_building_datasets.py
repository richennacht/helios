"""Merge Google Open Buildings v3/Temporal heights with OSM buildings.

Google footprints are matched to the smallest OSM polygon containing their
documented centroid. Heights are averaged when both sources have a value and
the one available value is retained when only one source has one. No synthetic
height is introduced.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any


def _positive_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _osm_height(properties: dict[str, Any]) -> float | None:
    source = str(properties.get("height_source") or "").lower()
    if "fallback" in source or "unavailable" in source:
        return None
    return _positive_number(properties.get("height_m"))


def fuse_height_observations(
    observations: list[dict[str, Any]], reference_year: int | None = None
) -> tuple[float | None, list[str]]:
    """Average available independent height observations for one building.

    An independence group prevents a fused catalogue and its named upstream
    source from receiving duplicate weight. Historical observations are only
    included when their year matches ``reference_year``.
    """
    selected: dict[str, tuple[float, str]] = {}
    for observation in observations:
        year = observation.get("year")
        if year is not None and reference_year is not None and year != reference_year:
            continue
        height = _positive_number(observation.get("height_m"))
        if height is None:
            continue
        source_id = str(observation["source_id"])
        group = str(observation.get("independence_group") or source_id)
        selected.setdefault(group, (height, source_id))
    if not selected:
        return None, []
    values = [value for value, _ in selected.values()]
    return round(sum(values) / len(values), 2), [source for _, source in selected.values()]


def _rings(feature: dict[str, Any]) -> list[list[list[float]]]:
    geometry = feature.get("geometry") or {}
    coordinates = geometry.get("coordinates") or []
    if geometry.get("type") == "Polygon":
        return coordinates[:1]
    if geometry.get("type") == "MultiPolygon":
        return [polygon[0] for polygon in coordinates if polygon]
    return []


def _point_in_ring(point: tuple[float, float], ring: list[list[float]]) -> bool:
    x, y = point
    inside = False
    previous = ring[-1]
    for current in ring:
        x1, y1 = previous[:2]
        x2, y2 = current[:2]
        if (y1 > y) != (y2 > y):
            crossing_x = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < crossing_x:
                inside = not inside
        previous = current
    return inside


def _contains(feature: dict[str, Any], point: tuple[float, float]) -> bool:
    return any(_point_in_ring(point, ring) for ring in _rings(feature))


def _bbox_area(feature: dict[str, Any]) -> float:
    points = [point for ring in _rings(feature) for point in ring]
    if not points:
        return float("inf")
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return (max(xs) - min(xs)) * (max(ys) - min(ys))


def _google_centroid(feature: dict[str, Any]) -> tuple[float, float]:
    properties = feature.get("properties") or {}
    lon = properties.get("source_centroid_lon")
    lat = properties.get("source_centroid_lat")
    if lon is not None and lat is not None:
        return float(lon), float(lat)
    ring = _rings(feature)[0]
    points = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring
    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    )


def merge_collections(osm: dict[str, Any], google: dict[str, Any]) -> dict[str, Any]:
    osm_features = copy.deepcopy(osm.get("features") or [])
    google_features = copy.deepcopy(google.get("features") or [])
    matches: dict[int, list[dict[str, Any]]] = {}
    unmatched_google: list[dict[str, Any]] = []

    for google_feature in google_features:
        point = _google_centroid(google_feature)
        candidates = [
            (index, feature)
            for index, feature in enumerate(osm_features)
            if _contains(feature, point)
        ]
        if not candidates:
            unmatched_google.append(google_feature)
            continue
        osm_index, _ = min(candidates, key=lambda item: _bbox_area(item[1]))
        matches.setdefault(osm_index, []).append(google_feature)

    merged: list[dict[str, Any]] = []
    counts = {"averaged": 0, "osm_only": 0, "google_only": 0, "missing": 0}
    for index, osm_feature in enumerate(osm_features):
        properties = osm_feature.setdefault("properties", {})
        osm_height = _osm_height(properties)
        matched = matches.get(index, [])
        google_heights = [
            height
            for feature in matched
            if (height := _positive_number(feature.get("properties", {}).get("temporal_height_m")))
            is not None
        ]
        google_height = sum(google_heights) / len(google_heights) if google_heights else None
        fused_height, fused_sources = fuse_height_observations(
            [
                {"source_id": "openstreetmap", "height_m": osm_height},
                {"source_id": "google-open-buildings-temporal", "height_m": google_height},
            ]
        )
        properties["osm_height_m"] = osm_height
        properties["google_temporal_height_m"] = (
            round(google_height, 2) if google_height is not None else None
        )
        properties["height_m"] = fused_height
        properties["height_observation_sources"] = fused_sources
        properties["google_candidate_ids"] = [
            feature.get("properties", {}).get("candidate_id") for feature in matched
        ]
        properties["source_datasets"] = (
            ["OpenStreetMap", "Google Open Buildings v3 / Temporal v1"]
            if matched
            else ["OpenStreetMap"]
        )
        if osm_height is not None and google_height is not None:
            properties["height_source"] = "mean of OSM and Google Temporal heights"
            counts["averaged"] += 1
        elif osm_height is not None:
            properties["height_source"] = "OSM height (only available source)"
            counts["osm_only"] += 1
        elif google_height is not None:
            properties["height_source"] = "Google Temporal height (only available source)"
            counts["google_only"] += 1
        else:
            properties["height_source"] = "height unavailable in provided datasets"
            counts["missing"] += 1
        merged.append(osm_feature)

    for google_feature in unmatched_google:
        properties = google_feature.setdefault("properties", {})
        google_height = _positive_number(properties.get("temporal_height_m"))
        properties.update(
            {
                "osm_height_m": None,
                "google_temporal_height_m": google_height,
                "height_m": google_height,
                "height_source": "Google Temporal height (only available source)"
                if google_height is not None
                else "height unavailable in provided datasets",
                "source_datasets": ["Google Open Buildings v3 / Temporal v1"],
            }
        )
        counts["google_only" if google_height is not None else "missing"] += 1
        merged.append(google_feature)

    return {
        "type": "FeatureCollection",
        "name": "helios-merged-buildings-3d",
        "metadata": {
            "description": "Union of provided OSM and Google Open Buildings records",
            "matching_policy": "Google documented centroid inside smallest containing OSM polygon",
            "height_policy": "arithmetic mean of available source heights; one value passes through; none remains null",
            "synthetic_height_fallback": False,
            "input_counts": {"osm": len(osm_features), "google": len(google_features)},
            "output_count": len(merged),
            "height_result_counts": counts,
            "unmatched_google_count": len(unmatched_google),
        },
        "features": merged,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("osm", type=Path)
    parser.add_argument("google", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    osm = json.loads(args.osm.read_text(encoding="utf-8"))
    google = json.loads(args.google.read_text(encoding="utf-8"))
    result = merge_collections(osm, google)
    args.destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["metadata"], indent=2))


if __name__ == "__main__":
    main()
