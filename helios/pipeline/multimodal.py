"""AOI orchestration for the P2/P3/Person 4 multimodal handoff."""

from __future__ import annotations

from typing import Any

from helios.ranking.contracts import P5RankingRequest, RankingBundle
from helios.ranking.engine import rank_candidates


def rank_selected_aoi(request: P5RankingRequest, aoi: dict[str, Any]) -> RankingBundle:
    """Filter aligned P2/P3/confidence rows to an AOI, then run Person 4.

    A candidate is visualized/analyzed only when every footprint vertex is
    strictly inside the AOI. Surrounding context belongs in the upstream P2
    feature calculation and is not discarded by this visual selection rule.
    """
    selected = {
        row.candidate_id
        for row in request.p2_table
        if _geometry_strictly_inside(row.geometry, aoi)
    }
    if not selected:
        raise ValueError("selected AOI contains no complete candidate footprints")

    payload = request.model_dump(mode="json")
    payload["p2_table"] = [row for row in payload["p2_table"] if row["candidate_id"] in selected]
    payload["p3_table"] = [row for row in payload["p3_table"] if row["candidate_id"] in selected]
    payload["confidence_table"] = [
        row for row in payload["confidence_table"] if row["candidate_id"] in selected
    ]
    payload["scenario"]["top_k"] = min(payload["scenario"]["top_k"], len(selected))
    filtered = P5RankingRequest.model_validate(payload)
    return rank_candidates(filtered)


def _geometry_strictly_inside(geometry: dict[str, Any], aoi: dict[str, Any]) -> bool:
    if aoi.get("type") != "Polygon":
        return False
    aoi_ring = aoi.get("coordinates", [[]])[0]
    if geometry.get("type") == "Point":
        point = geometry.get("coordinates", [])
        return _point_strictly_inside(point, aoi_ring)
    if geometry.get("type") != "Polygon":
        return False
    building_ring = geometry.get("coordinates", [[]])[0]
    return bool(building_ring) and all(
        _point_strictly_inside(point, aoi_ring) for point in building_ring
    )


def _point_strictly_inside(point: list[float], ring: list[list[float]]) -> bool:
    if len(point) < 2 or len(ring) < 4:
        return False
    x, y = point[:2]
    inside = False
    for index in range(len(ring) - 1):
        x1, y1 = ring[index][:2]
        x2, y2 = ring[index + 1][:2]
        cross = (y - y1) * (x2 - x1) - (x - x1) * (y2 - y1)
        if (
            abs(cross) < 1e-10
            and min(x1, x2) <= x <= max(x1, x2)
            and min(y1, y2) <= y <= max(y1, y2)
        ):
            return False
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-12) + x1:
            inside = not inside
    return inside
