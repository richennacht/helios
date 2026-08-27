"""Safe roof-plane geometry calculations.

The module does not emit learned predictions without validated model weights and
an image/elevation input. It supports provenance-labelled simulation so the 3D
area effect can be demonstrated without presenting synthetic values as observations.
"""

from __future__ import annotations

from math import cos, pi
from typing import Any

from helios.contracts.models import RoofGeometryPrediction, RoofType

EARTH_RADIUS_M = 6_371_008.8


def _polygon_ring(geometry: dict[str, Any]) -> list[list[float]]:
    candidate = geometry.get("geometry", geometry)
    if candidate.get("type") != "Polygon":
        raise ValueError("Only GeoJSON Polygon geometry is supported")
    coordinates = candidate.get("coordinates")
    if not coordinates or len(coordinates[0]) < 4:
        raise ValueError("Polygon must contain a closed ring with at least four coordinates")
    ring = coordinates[0]
    if ring[0] != ring[-1]:
        raise ValueError("Polygon ring must be closed")
    return ring


def horizontal_area_sqm(geometry: dict[str, Any]) -> float:
    """Approximate a small WGS84 polygon's area in a local metric plane."""
    ring = _polygon_ring(geometry)
    latitude = sum(float(point[1]) for point in ring[:-1]) / (len(ring) - 1)
    latitude_radians = latitude * pi / 180
    projected = [
        (
            EARTH_RADIUS_M * float(point[0]) * pi / 180 * cos(latitude_radians),
            EARTH_RADIUS_M * float(point[1]) * pi / 180,
        )
        for point in ring
    ]
    double_area = sum(
        x1 * y2 - x2 * y1
        for (x1, y1), (x2, y2) in zip(projected, projected[1:], strict=False)
    )
    return abs(double_area) / 2


def calculate_surface_area(geometry: dict[str, Any], pitch_deg: float) -> tuple[float, float]:
    """Return horizontal and sloped surface area for an explicit pitch simulation."""
    if not 0 <= pitch_deg <= 45:
        raise ValueError("Pitch must be between 0 and 45 degrees")
    horizontal = horizontal_area_sqm(geometry)
    surface = horizontal / cos(pitch_deg * pi / 180)
    return horizontal, surface


def simulate_geometry(
    geometry: dict[str, Any],
    *,
    pitch_deg: float,
    azimuth_deg: float,
    roof_type: RoofType,
    provenance: str,
) -> RoofGeometryPrediction:
    """Simulate roof geometry from explicit inputs; never claim model confidence."""
    if not provenance.strip():
        raise ValueError("Simulation provenance is required")
    if not 0 <= azimuth_deg <= 360:
        raise ValueError("Azimuth must be between 0 and 360 degrees")
    horizontal, surface = calculate_surface_area(geometry, pitch_deg)
    return RoofGeometryPrediction(
        pitch_deg=round(pitch_deg, 2),
        azimuth_deg=round(azimuth_deg, 2),
        horizontal_area_sqm=round(horizontal, 2),
        surface_area_sqm=round(surface, 2),
        roof_type=roof_type,
        confidence=None,
        decision_status="simulation_only",
        provenance=provenance,
    )
