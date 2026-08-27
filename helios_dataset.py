"""
HELIOS Dataset Loader and Real-World Integration Adapter
========================================================
Loads and integrates datasets from the HELIOS platform repository:
- Candidate building footprints from Google Open Buildings (data/sample/source_layers/candidate_buildings.geojson)
- Area of Interest (data/sample/source_layers/kharghar_aoi.geojson)
- Solar economics & NASA POWER irradiance features (data/sample/features/solar_economics/)
- Person 4 multi-criteria ranking fixtures (data/fixtures/person4/person4-request.json)
- Metric projection transformers (WGS84 lat/lon <-> Local tangent plane in meters)
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.ops import transform

from layout_optimizer import (
    ConstraintRules,
    PanelLayoutOptimizer,
    PanelSpec,
    PlacementResult,
    SolarAccessMatrix,
    optimize_panel_placement,
)

# Earth WGS84 semi-major axis in meters
WGS84_A = 6378137.0


# ============================================================================
# Geodetic / Metric Coordinate Projection Helpers
# ============================================================================

def latlon_to_local_meters(lon: float, lat: float, ref_lon: float, ref_lat: float) -> Tuple[float, float]:
    """Convert WGS84 (lon, lat) to local Cartesian plane (x_meters, y_meters) relative to a reference point."""
    rad = math.pi / 180.0
    lat_rad = math.radians(ref_lat)
    dx = (lon - ref_lon) * rad * WGS84_A * math.cos(lat_rad)
    dy = (lat - ref_lat) * rad * WGS84_A
    return dx, dy


def local_meters_to_latlon(x: float, y: float, ref_lon: float, ref_lat: float) -> Tuple[float, float]:
    """Convert local Cartesian coordinates (x_meters, y_meters) back to WGS84 (lon, lat)."""
    rad = math.pi / 180.0
    lat_rad = math.radians(ref_lat)
    lon = ref_lon + (x / (WGS84_A * math.cos(lat_rad) * rad))
    lat = ref_lat + (y / (WGS84_A * rad))
    return lon, lat


def project_polygon_to_meters(poly: Polygon, ref_lon: float, ref_lat: float) -> Polygon:
    """Project a Shapely Polygon from WGS84 coordinates to local metric coordinates in meters."""
    def _proj(x, y, z=None):
        return latlon_to_local_meters(x, y, ref_lon, ref_lat)
    return transform(_proj, poly)


def project_polygon_to_latlon(poly: Polygon, ref_lon: float, ref_lat: float) -> Polygon:
    """Project a Shapely Polygon from local metric coordinates in meters back to WGS84."""
    def _proj(x, y, z=None):
        return local_meters_to_latlon(x, y, ref_lon, ref_lat)
    return transform(_proj, poly)


# ============================================================================
# Dataset Models & Data Structures
# ============================================================================

@dataclass
class BuildingCandidate:
    """Represents a building candidate from the HELIOS dataset."""
    candidate_id: str
    geometry_wgs84: Polygon
    footprint_area_m2: float
    height_m: float
    confidence: float
    centroid_lat: float
    centroid_lon: float
    aoi_id: str = "kharghar-v1"
    raw_properties: Dict[str, Any] = field(default_factory=dict)

    @property
    def metric_polygon(self) -> Polygon:
        """Roof polygon projected into local metric coordinates centered at building centroid."""
        return project_polygon_to_meters(
            self.geometry_wgs84,
            ref_lon=self.centroid_lon,
            ref_lat=self.centroid_lat,
        )


@dataclass
class BuildingPVResult:
    """Optimization and solar energy yield result for a specific building candidate."""
    candidate: BuildingCandidate
    placement_result: PlacementResult
    panel_coordinates_wgs84: np.ndarray  # Shape (N, 4, 2) in (lon, lat)
    annual_poa_kwh_m2: float
    annual_yield_kwh: float
    estimated_cost_inr: float
    annual_energy_value_inr: float
    simple_payback_years: float
    performance_ratio: float = 0.80

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate.candidate_id,
            "footprint_area_m2": round(self.candidate.footprint_area_m2, 2),
            "building_height_m": self.candidate.height_m,
            "total_panel_count": self.placement_result.total_panel_count,
            "installed_dc_capacity_kwp": round(self.placement_result.installed_dc_capacity_kwp, 3),
            "annual_yield_kwh": round(self.annual_yield_kwh, 2),
            "estimated_cost_inr": round(self.estimated_cost_inr, 2),
            "annual_energy_value_inr": round(self.annual_energy_value_inr, 2),
            "simple_payback_years": round(self.simple_payback_years, 2) if self.simple_payback_years > 0 else None,
            "metrics": self.placement_result.metrics,
        }

    def to_geojson_feature(self) -> Dict[str, Any]:
        """Export placed panels and building as georeferenced GeoJSON FeatureCollection."""
        features = [
            {
                "type": "Feature",
                "geometry": mapping(self.candidate.geometry_wgs84),
                "properties": {
                    "layer": "building_footprint",
                    "candidate_id": self.candidate.candidate_id,
                    "height_m": self.candidate.height_m,
                    "installed_dc_capacity_kwp": round(self.placement_result.installed_dc_capacity_kwp, 3),
                    "annual_yield_kwh": round(self.annual_yield_kwh, 2),
                }
            }
        ]

        # Add each panel polygon in WGS84
        for idx in range(self.placement_result.total_panel_count):
            coords = self.panel_coordinates_wgs84[idx].tolist()
            # Close polygon ring
            coords.append(coords[0])
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coords]
                },
                "properties": {
                    "layer": "solar_panel",
                    "candidate_id": self.candidate.candidate_id,
                    "panel_index": idx + 1,
                    "rated_power_w": self.placement_result.panel_spec.rated_power_w,
                }
            })

        return {
            "type": "FeatureCollection",
            "properties": self.to_dict(),
            "features": features,
        }


# ============================================================================
# HELIOS Dataset Loaders
# ============================================================================

class HeliosDataLoader:
    """Provides structured access to all data layers in the HELIOS repository."""

    def __init__(self, base_data_dir: Union[str, Path] = "data"):
        self.base_data_dir = Path(base_data_dir)

    def load_candidate_buildings(
        self, relative_path: str = "sample/source_layers/candidate_buildings.geojson"
    ) -> List[BuildingCandidate]:
        """Load building candidate footprints from GeoJSON."""
        file_path = self.base_data_dir / relative_path
        if not file_path.exists():
            raise FileNotFoundError(f"Candidate buildings file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        candidates = []
        for feature in data.get("features", []):
            geom = shape(feature["geometry"])
            if not isinstance(geom, Polygon):
                continue
            if not geom.is_valid:
                geom = geom.buffer(0)

            props = feature.get("properties", {})
            c_id = props.get("candidate_id", f"candidate_{len(candidates)+1}")
            area_m2 = props.get("source_footprint_area_m2", float(geom.area * 111320 * 111320 * math.cos(math.radians(19.04))))
            height_m = props.get("temporal_height_m", 10.0)
            confidence = props.get("source_confidence", 0.8)
            lat = props.get("source_centroid_lat", geom.centroid.y)
            lon = props.get("source_centroid_lon", geom.centroid.x)

            candidates.append(
                BuildingCandidate(
                    candidate_id=c_id,
                    geometry_wgs84=geom,
                    footprint_area_m2=area_m2,
                    height_m=height_m,
                    confidence=confidence,
                    centroid_lat=lat,
                    centroid_lon=lon,
                    aoi_id=props.get("aoi_id", "kharghar-v1"),
                    raw_properties=props,
                )
            )
        return candidates

    def load_kharghar_aoi(
        self, relative_path: str = "sample/source_layers/kharghar_aoi.geojson"
    ) -> Polygon:
        """Load Area of Interest boundary polygon."""
        file_path = self.base_data_dir / relative_path
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        feature = data["features"][0]
        return shape(feature["geometry"])

    def load_solar_economics_assumptions(
        self, relative_path: str = "sample/features/solar_economics/solar_economic_features.json"
    ) -> Dict[str, Any]:
        """Load solar economics constants (annual POA irradiance, CAPEX INR/kWp, tariff)."""
        file_path = self.base_data_dir / relative_path
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_person4_request_fixture(
        self, relative_path: str = "fixtures/person4/person4-request.json"
    ) -> Dict[str, Any]:
        """Load Person 4 multi-criteria ranking fixture dataset."""
        file_path = self.base_data_dir / relative_path
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_manifests(self) -> List[Dict[str, Any]]:
        """Load all data source manifests and checksums."""
        manifest_dir = self.base_data_dir / "manifests"
        manifests = []
        if manifest_dir.exists():
            for p in manifest_dir.glob("*.json"):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        manifests.append(json.load(f))
                except Exception:
                    pass
        return manifests


# ============================================================================
# High-Level Optimization Pipeline on HELIOS Real Candidates
# ============================================================================

def optimize_building_pv(
    candidate: BuildingCandidate,
    constraint_rules: Optional[ConstraintRules] = None,
    panel_spec: Optional[PanelSpec] = None,
    annual_poa_kwh_m2: float = 1800.0,  # NASA POWER Kharghar 2025 Climatology
    capex_inr_per_kwp: float = 50000.0,  # INR 50,000 / kWp
    tariff_inr_per_kwh: float = 8.0,     # INR 8.0 / kWh
    performance_ratio: float = 0.80,     # Standard 80% PR
) -> BuildingPVResult:
    """Run constraint-aware layout optimization on a real HELIOS building candidate.

    1. Projects building footprint to local metric space in meters.
    2. Enforces setbacks (e.g. 1.0m parapet setback), maintenance aisles, and 80% solar access.
    3. Solves optimal PV panel placement and calculates explicit coordinates.
    4. Projects coordinates back to WGS84 georeferenced coordinates.
    5. Calculates annual solar energy yield (kWh), system cost, and financial metrics.
    """
    c_rules = constraint_rules or ConstraintRules(
        parapet_setback=1.0,
        obstacle_setback=0.5,
        maintenance_aisle_width=0.8,
        maintenance_aisle_frequency_rows=2,
        reserved_space_ratio=0.15,
        min_solar_access=0.80,
    )
    p_spec = panel_spec or PanelSpec(
        length=2.2,
        width=1.1,
        rated_power_w=550.0,
        tilt_deg=15.0,
        azimuth_deg=180.0,
    )

    # Metric roof polygon centered at building centroid
    roof_metric = candidate.metric_polygon

    # Run optimizer
    placement = optimize_panel_placement(
        roof_polygons=roof_metric,
        obstacle_polygons=[],
        solar_access_matrix=0.95,  # High baseline solar access for unshaded rooftop
        constraint_rules=c_rules,
        panel_spec=p_spec,
    )

    # Project panel coordinates back to WGS84
    n_panels = placement.total_panel_count
    if n_panels > 0:
        wgs84_coords = np.zeros((n_panels, 4, 2), dtype=np.float64)
        for i in range(n_panels):
            for corner_idx in range(4):
                mx, my = placement.panel_coordinates[i, corner_idx]
                lon, lat = local_meters_to_latlon(
                    mx, my, ref_lon=candidate.centroid_lon, ref_lat=candidate.centroid_lat
                )
                wgs84_coords[i, corner_idx] = [lon, lat]
    else:
        wgs84_coords = np.empty((0, 4, 2), dtype=np.float64)

    # Calculate Solar Yield and Economics
    installed_kwp = placement.installed_dc_capacity_kwp
    shading_factor = placement.metrics.get("average_solar_access", 0.95)
    annual_yield_kwh = installed_kwp * annual_poa_kwh_m2 * shading_factor * performance_ratio
    estimated_cost_inr = installed_kwp * capex_inr_per_kwp
    annual_energy_value_inr = annual_yield_kwh * tariff_inr_per_kwh
    payback_years = (estimated_cost_inr / annual_energy_value_inr) if annual_energy_value_inr > 0 else 0.0

    return BuildingPVResult(
        candidate=candidate,
        placement_result=placement,
        panel_coordinates_wgs84=wgs84_coords,
        annual_poa_kwh_m2=annual_poa_kwh_m2,
        annual_yield_kwh=annual_yield_kwh,
        estimated_cost_inr=estimated_cost_inr,
        annual_energy_value_inr=annual_energy_value_inr,
        simple_payback_years=payback_years,
        performance_ratio=performance_ratio,
    )


def optimize_all_candidates(
    base_data_dir: Union[str, Path] = "data",
    constraint_rules: Optional[ConstraintRules] = None,
    panel_spec: Optional[PanelSpec] = None,
) -> List[BuildingPVResult]:
    """Load all real candidates from HELIOS dataset and execute PV optimization for each."""
    loader = HeliosDataLoader(base_data_dir=base_data_dir)
    candidates = loader.load_candidate_buildings()
    results = []

    for cand in candidates:
        res = optimize_building_pv(
            candidate=cand,
            constraint_rules=constraint_rules,
            panel_spec=panel_spec,
        )
        results.append(res)

    return results
