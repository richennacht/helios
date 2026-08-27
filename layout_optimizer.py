"""
Constraint-Aware Solar Panel Layout Optimizer
=============================================
A high-performance geometric optimizer for solar photovoltaic (PV) rooftop and
ground-mount installations using Shapely, SciPy, and NumPy.

Author: Antigravity (Advanced Agentic Coding)
Role: Constraint-Aware Panel Layout Optimizer
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
from scipy.interpolate import RegularGridInterpolator
from shapely import affinity, prepared
from shapely.geometry import (
    GeometryCollection,
    MultiPolygon,
    Point,
    Polygon,
    box,
    mapping,
    shape,
)
from shapely.ops import unary_union


# ============================================================================
# Data Models & Configurations
# ============================================================================

@dataclass
class PanelSpec:
    """Hardware specifications for a photovoltaic module.

    Attributes:
        length: Module length in meters (default 2.2m for standard utility/commercial modules).
        width: Module width in meters (default 1.1m).
        rated_power_w: Rated DC peak power per module in Watts (default 550.0 Wp).
        tilt_deg: Installation tilt angle in degrees (default 15.0°).
        azimuth_deg: Module azimuth angle in degrees (default 180.0° = South facing).
        orientation: 'portrait' (length along pitch) or 'landscape' (width along pitch).
        inter_panel_gap: Clamping / physical spacing between panels along a row in meters.
    """
    length: float = 2.2
    width: float = 1.1
    rated_power_w: float = 550.0
    tilt_deg: float = 15.0
    azimuth_deg: float = 180.0
    orientation: str = "portrait"
    inter_panel_gap: float = 0.02

    @property
    def module_area(self) -> float:
        """Physical surface area of a single module in square meters."""
        return self.length * self.width

    @property
    def projected_dimensions(self) -> Tuple[float, float]:
        """Ground footprint dimensions (width_along_row, length_along_pitch) in meters.

        Accounts for tilt angle shortening along the pitch axis.
        """
        tilt_rad = math.radians(self.tilt_deg)
        cos_tilt = math.cos(tilt_rad)

        if self.orientation.lower() == "portrait":
            # Width along East-West row, Length tilted along North-South pitch
            dim_x = self.width
            dim_y = self.length * cos_tilt
        else:
            # Length along East-West row, Width tilted along North-South pitch
            dim_x = self.length
            dim_y = self.width * cos_tilt

        return float(dim_x), float(dim_y)


@dataclass
class ConstraintRules:
    """Setback, maintenance, shading, and reserved space constraint policies.

    Attributes:
        parapet_setback: Setback distance from roof perimeter / parapet in meters (default 1.0m).
        obstacle_setback: Clearance distance around obstacles (HVAC, skylights, vents) in meters (default 0.5m).
        maintenance_aisle_width: Width of maintenance aisles/walkways in meters (default 0.8m).
        maintenance_aisle_frequency_rows: Number of panel rows per table before inserting a maintenance aisle (default 2).
        maintenance_aisle_frequency_cols: Number of panel columns per table before inserting a cross-aisle (0 = disabled).
        reserved_space_ratio: Fraction of roof / capacity reserved for balance of system / walkways / future (default 0.15 = 15%).
        min_solar_access: Minimum required solar access percentage or fraction (default 0.80 = 80%).
        row_pitch: Center-to-center or edge-to-edge row pitch in meters. If None, calculated automatically.
        optimize_offsets: Whether to sweep grid translation offsets to find maximum panel yield (default True).
        offset_grid_resolution: Number of grid offset search steps per dimension (default 6).
    """
    parapet_setback: float = 1.0
    obstacle_setback: float = 0.5
    maintenance_aisle_width: float = 0.8
    maintenance_aisle_frequency_rows: int = 2
    maintenance_aisle_frequency_cols: int = 0
    reserved_space_ratio: float = 0.15
    min_solar_access: float = 0.80
    row_pitch: Optional[float] = None
    optimize_offsets: bool = True
    offset_grid_resolution: int = 6


class SolarAccessMatrix:
    """Encapsulates spatial solar access data with fast 2D interpolation.

    Supports:
    - 2D numpy arrays with explicit georeferenced bounding box `(minx, miny, maxx, maxy)`.
    - Custom callable functions `f(x, y) -> float` (in range 0.0 to 1.0 or 0 to 100%).
    - Constant uniform solar access values (e.g. 1.0 for 100%).
    """

    def __init__(
        self,
        data: Union[np.ndarray, Sequence[Sequence[float]], Callable[[float, float], float], float, int, None] = None,
        bounds: Optional[Tuple[float, float, float, float]] = None,
    ):
        self.bounds = bounds
        self._interpolator: Optional[RegularGridInterpolator] = None
        self._callable: Optional[Callable[[float, float], float]] = None
        self._constant: Optional[float] = None

        if data is None:
            self._constant = 1.0
        elif isinstance(data, (int, float)):
            val = float(data)
            self._constant = val / 100.0 if val > 1.0 else val
        elif callable(data):
            self._callable = data
        elif isinstance(data, (np.ndarray, list, tuple)):
            arr = np.asarray(data, dtype=np.float64)
            if arr.ndim != 2:
                raise ValueError(f"Solar access matrix must be 2-dimensional, got shape {arr.shape}")
            
            # Normalize to 0.0 - 1.0 if given in 0 - 100%
            if np.nanmax(arr) > 1.0:
                arr = arr / 100.0

            self.matrix = arr
            ny, nx = arr.shape

            if bounds is None:
                # Default unit coordinate box if bounds not provided
                minx, miny, maxx, maxy = 0.0, 0.0, float(nx), float(ny)
            else:
                minx, miny, maxx, maxy = bounds

            xs = np.linspace(minx, maxx, nx)
            ys = np.linspace(miny, maxy, ny)

            # RegularGridInterpolator expects strictly ascending coordinates
            self._interpolator = RegularGridInterpolator(
                (ys, xs),
                arr,
                method="linear",
                bounds_error=False,
                fill_value=1.0,
            )
        else:
            raise TypeError(f"Unsupported solar access matrix data type: {type(data)}")

    def sample_point(self, x: float, y: float) -> float:
        """Sample solar access at a single point (x, y). Returns float in [0.0, 1.0]."""
        if self._constant is not None:
            return self._constant
        if self._callable is not None:
            val = self._callable(x, y)
            return float(val / 100.0 if val > 1.0 else val)
        if self._interpolator is not None:
            val = float(self._interpolator((y, x)))
            return max(0.0, min(1.0, val))
        return 1.0

    def sample_points(self, points: np.ndarray) -> np.ndarray:
        """Vectorized sample of solar access for array of points shape (N, 2)."""
        if len(points) == 0:
            return np.empty(0, dtype=np.float64)
        if self._constant is not None:
            return np.full(len(points), self._constant, dtype=np.float64)
        if self._callable is not None:
            return np.array([self.sample_point(p[0], p[1]) for p in points], dtype=np.float64)
        if self._interpolator is not None:
            # Interpolator expects (y, x)
            coords = np.column_stack([points[:, 1], points[:, 0]])
            vals = self._interpolator(coords)
            return np.clip(vals, 0.0, 1.0)
        return np.ones(len(points), dtype=np.float64)

    def evaluate_polygon_solar_access(self, poly: Polygon) -> float:
        """Evaluate average solar access over the corners and centroid of a polygon."""
        coords = np.array(poly.exterior.coords)[:-1]  # 4 corners
        centroid = np.array([[poly.centroid.x, poly.centroid.y]])
        eval_points = np.vstack([coords, centroid])
        samples = self.sample_points(eval_points)
        return float(np.mean(samples))


@dataclass
class PlacementResult:
    """Complete output result of the panel placement optimization.

    Attributes:
        panel_coordinates: Explicit numpy array of 4 corners (x, y) for every placed panel, shape (N, 4, 2).
        total_panel_count: Total number of placed solar panels N.
        installed_dc_capacity_kwp: Installed DC system capacity in kWp (N * module_rated_power_w / 1000.0).
        panel_polygons: List of Shapely Polygon objects for all placed panels.
        net_usable_polygon: Shapely Polygon or MultiPolygon representing the net usable roof area.
        roof_polygon: Shapely Polygon or MultiPolygon of the input roof.
        obstacle_polygons: List of Shapely Polygons of the input obstacles.
        solar_access_scores: Numpy array of mean solar access scores for each placed panel.
        panel_spec: Panel specifications used.
        constraint_rules: Constraint rules used.
        metrics: Detailed dictionary of layout performance and geometric metrics.
    """
    panel_coordinates: np.ndarray
    total_panel_count: int
    installed_dc_capacity_kwp: float
    panel_polygons: List[Polygon] = field(default_factory=list)
    net_usable_polygon: Union[Polygon, MultiPolygon] = field(default_factory=Polygon)
    roof_polygon: Union[Polygon, MultiPolygon] = field(default_factory=Polygon)
    obstacle_polygons: List[Polygon] = field(default_factory=list)
    solar_access_scores: np.ndarray = field(default_factory=lambda: np.empty(0))
    panel_spec: PanelSpec = field(default_factory=PanelSpec)
    constraint_rules: ConstraintRules = field(default_factory=ConstraintRules)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert placement summary and panel coordinates to a standard Python dictionary."""
        return {
            "total_panel_count": self.total_panel_count,
            "installed_dc_capacity_kwp": round(self.installed_dc_capacity_kwp, 3),
            "panel_coordinates": self.panel_coordinates.tolist(),
            "solar_access_scores": [round(float(s), 4) for s in self.solar_access_scores],
            "metrics": self.metrics,
        }

    def to_geojson(self) -> Dict[str, Any]:
        """Export placed panels and roof layers to standard GeoJSON FeatureCollection."""
        features = []

        # Roof feature
        if not self.roof_polygon.is_empty:
            features.append({
                "type": "Feature",
                "geometry": mapping(self.roof_polygon),
                "properties": {"layer": "roof_boundary", "area_m2": round(self.roof_polygon.area, 2)}
            })

        # Usable area feature
        if not self.net_usable_polygon.is_empty:
            features.append({
                "type": "Feature",
                "geometry": mapping(self.net_usable_polygon),
                "properties": {"layer": "net_usable_area", "area_m2": round(self.net_usable_polygon.area, 2)}
            })

        # Obstacles features
        for idx, obs in enumerate(self.obstacle_polygons):
            features.append({
                "type": "Feature",
                "geometry": mapping(obs),
                "properties": {"layer": "obstacle", "id": idx, "area_m2": round(obs.area, 2)}
            })

        # Placed panel features
        for idx, (poly, score) in enumerate(zip(self.panel_polygons, self.solar_access_scores)):
            features.append({
                "type": "Feature",
                "geometry": mapping(poly),
                "properties": {
                    "layer": "solar_panel",
                    "panel_id": idx + 1,
                    "rated_power_w": self.panel_spec.rated_power_w,
                    "solar_access": round(float(score), 4),
                    "tilt_deg": self.panel_spec.tilt_deg,
                    "azimuth_deg": self.panel_spec.azimuth_deg,
                }
            })

        return {
            "type": "FeatureCollection",
            "properties": {
                "total_panel_count": self.total_panel_count,
                "installed_dc_capacity_kwp": round(self.installed_dc_capacity_kwp, 3),
                "module_rating_w": self.panel_spec.rated_power_w,
            },
            "features": features,
        }


# ============================================================================
# Geometry Ingestion & Conversion Utilities
# ============================================================================

def _to_shapely_polygon(
    geom: Union[Polygon, MultiPolygon, Sequence[Sequence[float]], Sequence[Tuple[float, float]], Dict[str, Any]]
) -> Union[Polygon, MultiPolygon]:
    """Convert various input formats (coordinates, GeoJSON, Shapely) into a valid Shapely Polygon."""
    if isinstance(geom, (Polygon, MultiPolygon)):
        poly = geom
    elif isinstance(geom, dict):
        if "coordinates" in geom or "type" in geom:
            poly = shape(geom)
        else:
            raise ValueError(f"Invalid GeoJSON dictionary geometry: {geom}")
    elif isinstance(geom, (list, tuple, np.ndarray)):
        arr = np.asarray(geom)
        if arr.ndim == 2 and arr.shape[1] == 2:
            poly = Polygon(arr)
        elif arr.ndim == 3 and arr.shape[2] == 2:
            # MultiPolygon or polygon with interior rings
            polys = [Polygon(p) for p in arr if len(p) >= 3]
            poly = unary_union(polys)
        else:
            raise ValueError(f"Cannot parse coordinate array of shape {arr.shape} into polygon.")
    else:
        raise TypeError(f"Unsupported geometry type: {type(geom)}")

    if not poly.is_valid:
        poly = poly.buffer(0)
    return poly


def _normalize_obstacle_list(
    obstacles: Union[Sequence[Any], Polygon, MultiPolygon, None]
) -> List[Polygon]:
    """Normalize obstacles input into a flat list of valid Shapely Polygon objects."""
    if obstacles is None:
        return []
    if isinstance(obstacles, (Polygon, MultiPolygon)):
        if isinstance(obstacles, Polygon):
            return [obstacles] if not obstacles.is_empty else []
        return [p for p in obstacles.geoms if not p.is_empty]

    res = []
    for obs in obstacles:
        poly = _to_shapely_polygon(obs)
        if isinstance(poly, Polygon) and not poly.is_empty:
            res.append(poly)
        elif isinstance(poly, MultiPolygon):
            res.extend([p for p in poly.geoms if not p.is_empty])
    return res


# ============================================================================
# Core Layout Optimizer Engine
# ============================================================================

class PanelLayoutOptimizer:
    """High-performance constraint-aware solar PV panel packing engine."""

    def __init__(
        self,
        panel_spec: Optional[PanelSpec] = None,
        constraint_rules: Optional[ConstraintRules] = None,
    ):
        self.panel_spec = panel_spec or PanelSpec()
        self.constraint_rules = constraint_rules or ConstraintRules()

    def calculate_default_pitch(self) -> float:
        """Compute optimal inter-row pitch to prevent inter-row shading.

        For tilted modules, shadow length during low solar elevation (e.g. winter solstice at ~25°-30° solar elevation)
        requires spacing = L * cos(tilt) + L * sin(tilt) / tan(solar_elevation).
        For flat modules (tilt=0°), spacing = length + inter-row buffer (0.05m).
        """
        dim_x, dim_y = self.panel_spec.projected_dimensions
        if self.panel_spec.tilt_deg <= 1.0:
            return dim_y + 0.05

        tilt_rad = math.radians(self.panel_spec.tilt_deg)
        # Solar design altitude angle: standard ~28° minimum winter sun altitude for mid-latitudes
        sun_altitude_rad = math.radians(28.0)
        
        # Module vertical rise
        vertical_height = (self.panel_spec.length if self.panel_spec.orientation == "portrait" else self.panel_spec.width) * math.sin(tilt_rad)
        shadow_clearance = vertical_height / math.tan(sun_altitude_rad)

        # Total center-to-center pitch
        calculated_pitch = dim_y + shadow_clearance
        return max(dim_y + 0.3, float(calculated_pitch))

    def compute_net_usable_domain(
        self,
        roof: Union[Polygon, MultiPolygon],
        obstacles: List[Polygon],
    ) -> Union[Polygon, MultiPolygon]:
        """Apply parapet setbacks and obstacle clearances to compute the net usable geometry.

        1. Inset roof perimeter by `parapet_setback`.
        2. Expand obstacle footprints by `obstacle_setback`.
        3. Difference the buffered obstacles from the inset roof polygon.
        """
        # Step 1: Inset roof perimeter
        if self.constraint_rules.parapet_setback > 0:
            inset_roof = roof.buffer(-self.constraint_rules.parapet_setback)
        else:
            inset_roof = roof

        if inset_roof.is_empty:
            return Polygon()

        # Step 2: Expand obstacle footprints
        if obstacles:
            buffered_obstacles = []
            for obs in obstacles:
                if self.constraint_rules.obstacle_setback > 0:
                    buffered_obstacles.append(obs.buffer(self.constraint_rules.obstacle_setback))
                else:
                    buffered_obstacles.append(obs)
            obstacles_union = unary_union(buffered_obstacles)
            net_domain = inset_roof.difference(obstacles_union)
        else:
            net_domain = inset_roof

        if not net_domain.is_valid:
            net_domain = net_domain.buffer(0)

        return net_domain

    def _generate_candidate_grid(
        self,
        domain_local: Union[Polygon, MultiPolygon],
        offset_x: float,
        offset_y: float,
        dim_x: float,
        dim_y: float,
        step_x: float,
        step_y: float,
        aisle_w: float,
        aisle_freq_rows: int,
        aisle_freq_cols: int,
    ) -> List[Polygon]:
        """Generate candidate panel rectangles in the local coordinate frame with maintenance aisles."""
        minx, miny, maxx, maxy = domain_local.bounds
        candidates = []

        # Iterate Y (Pitch / Rows) from miny to maxy
        curr_y = miny + offset_y
        row_idx = 0

        while curr_y + dim_y <= maxy:
            # Check if an East-West maintenance aisle is required before this row
            if aisle_freq_rows > 0 and row_idx > 0 and (row_idx % aisle_freq_rows == 0):
                curr_y += aisle_w
                if curr_y + dim_y > maxy:
                    break

            # Iterate X (Along Row) from minx to maxx
            curr_x = minx + offset_x
            col_idx = 0

            while curr_x + dim_x <= maxx:
                # Check if a North-South cross aisle is required before this column
                if aisle_freq_cols > 0 and col_idx > 0 and (col_idx % aisle_freq_cols == 0):
                    curr_x += aisle_w
                    if curr_x + dim_x > maxx:
                        break

                # Create panel box in local frame
                p_box = box(curr_x, curr_y, curr_x + dim_x, curr_y + dim_y)
                candidates.append(p_box)

                # Advance to next module in the row
                curr_x += step_x
                col_idx += 1

            # Advance to next row
            curr_y += step_y
            row_idx += 1

        return candidates

    def optimize_placement(
        self,
        roof_input: Union[Polygon, MultiPolygon, Sequence[Any], Dict[str, Any]],
        obstacles_input: Union[Sequence[Any], Polygon, MultiPolygon, None] = None,
        solar_access_input: Union[SolarAccessMatrix, np.ndarray, Sequence[Sequence[float]], Callable[[float, float], float], float, int, None] = None,
    ) -> PlacementResult:
        """Execute constraint-aware panel layout optimization.

        Parameters:
            roof_input: Roof polygon(s), coordinate sequences, or GeoJSON dict.
            obstacles_input: Obstacle polygon(s) to avoid.
            solar_access_input: Solar access matrix, grid, or callable function.

        Returns:
            PlacementResult with explicit coordinates array (N, 4, 2), count, and kWp capacity.
        """
        start_time = time.perf_counter()

        # Ingest and validate geometries
        roof_poly = _to_shapely_polygon(roof_input)
        obstacle_polys = _normalize_obstacle_list(obstacles_input)
        solar_access = (
            solar_access_input
            if isinstance(solar_access_input, SolarAccessMatrix)
            else SolarAccessMatrix(solar_access_input, bounds=roof_poly.bounds if not roof_poly.is_empty else None)
        )

        # Normalize minimum solar access threshold (accepts 0.80 or 80.0)
        min_solar_threshold = self.constraint_rules.min_solar_access
        if min_solar_threshold > 1.0:
            min_solar_threshold = min_solar_threshold / 100.0

        # Compute net usable domain
        net_domain = self.compute_net_usable_domain(roof_poly, obstacle_polys)
        if net_domain.is_empty:
            return self._empty_result(roof_poly, obstacle_polys, net_domain, start_time)

        # Module dimensions and pitch
        dim_x, dim_y = self.panel_spec.projected_dimensions
        step_x = dim_x + self.panel_spec.inter_panel_gap

        if self.constraint_rules.row_pitch is not None and self.constraint_rules.row_pitch > dim_y:
            step_y = self.constraint_rules.row_pitch
        else:
            step_y = self.calculate_default_pitch()

        aisle_w = self.constraint_rules.maintenance_aisle_width
        aisle_freq_rows = self.constraint_rules.maintenance_aisle_frequency_rows
        aisle_freq_cols = self.constraint_rules.maintenance_aisle_frequency_cols

        # Azimuth alignment rotation
        # Standard: 180° is South facing. Rotation angle aligns azimuth to South in local frame.
        rot_angle = self.panel_spec.azimuth_deg - 180.0
        centroid = net_domain.centroid

        if abs(rot_angle) > 1e-4:
            domain_local = affinity.rotate(net_domain, -rot_angle, origin=centroid)
        else:
            domain_local = net_domain

        # Optimize translation offsets (dx, dy) via grid search to maximize panel yield
        best_panels_global: List[Polygon] = []
        best_scores: List[float] = []

        if self.constraint_rules.optimize_offsets:
            n_steps = max(2, self.constraint_rules.offset_grid_resolution)
            offsets_x = np.linspace(0.0, step_x * 0.95, n_steps)
            offsets_y = np.linspace(0.0, step_y * 0.95, n_steps)
        else:
            offsets_x = [0.0]
            offsets_y = [0.0]

        prep_domain_local = prepared.prep(domain_local)

        for off_x in offsets_x:
            for off_y in offsets_y:
                candidates_local = self._generate_candidate_grid(
                    domain_local,
                    off_x,
                    off_y,
                    dim_x,
                    dim_y,
                    step_x,
                    step_y,
                    aisle_w,
                    aisle_freq_rows,
                    aisle_freq_cols,
                )

                # Filter panels strictly contained in net usable domain
                valid_local = [p for p in candidates_local if prep_domain_local.contains(p)]

                # Rotate back to global coordinate system
                if abs(rot_angle) > 1e-4:
                    valid_global = [affinity.rotate(p, rot_angle, origin=centroid) for p in valid_local]
                else:
                    valid_global = valid_local

                # Filter by solar access matrix (>= min_solar_access)
                passed_panels = []
                passed_scores = []
                for p_glob in valid_global:
                    score = solar_access.evaluate_polygon_solar_access(p_glob)
                    if score >= min_solar_threshold - 1e-5:
                        passed_panels.append(p_glob)
                        passed_scores.append(score)

                if len(passed_panels) > len(best_panels_global):
                    best_panels_global = passed_panels
                    best_scores = passed_scores

        # Apply Reserved Space Constraint (e.g. 15% reserved space)
        # If reserved_space_ratio > 0, reserve the required fraction by selecting the top (1 - ratio) highest-yield panels
        if self.constraint_rules.reserved_space_ratio > 0 and len(best_panels_global) > 0:
            keep_ratio = max(0.0, min(1.0, 1.0 - self.constraint_rules.reserved_space_ratio))
            target_count = int(math.floor(len(best_panels_global) * keep_ratio))
            
            # Sort by solar access score descending (retain the best unshaded panels)
            indexed_panels = list(zip(best_panels_global, best_scores))
            # Sort with secondary key of coordinate stability
            indexed_panels.sort(key=lambda item: (item[1], -item[0].centroid.y, item[0].centroid.x), reverse=True)
            
            final_selection = indexed_panels[:target_count]
            # Restore spatial layout ordering (top-to-bottom, left-to-right)
            final_selection.sort(key=lambda item: (-item[0].centroid.y, item[0].centroid.x))
            
            placed_panels = [item[0] for item in final_selection]
            placed_scores = np.array([item[1] for item in final_selection], dtype=np.float64)
        else:
            # Sort placed panels top-to-bottom, left-to-right
            indexed = list(zip(best_panels_global, best_scores))
            indexed.sort(key=lambda item: (-item[0].centroid.y, item[0].centroid.x))
            placed_panels = [item[0] for item in indexed]
            placed_scores = np.array([item[1] for item in indexed], dtype=np.float64)

        # Build explicit coordinates array of shape (N, 4, 2)
        total_count = len(placed_panels)
        if total_count > 0:
            coords_list = []
            for p in placed_panels:
                # Get the 4 corner points in standard order (excluding duplicate closing point)
                pts = np.array(p.exterior.coords)[:-1]
                coords_list.append(pts)
            panel_coords_array = np.array(coords_list, dtype=np.float64)
        else:
            panel_coords_array = np.empty((0, 4, 2), dtype=np.float64)

        # Calculate DC capacity in kWp
        installed_kwp = (total_count * self.panel_spec.rated_power_w) / 1000.0

        # Calculate performance metrics
        elapsed_sec = time.perf_counter() - start_time
        gross_roof_area = float(roof_poly.area)
        net_usable_area = float(net_domain.area)
        total_panel_area = total_count * self.panel_spec.module_area
        ground_coverage_ratio = (total_panel_area / gross_roof_area) if gross_roof_area > 0 else 0.0
        usable_area_utilization = (total_panel_area / net_usable_area) if net_usable_area > 0 else 0.0
        avg_solar_access = float(np.mean(placed_scores)) if total_count > 0 else 0.0

        metrics = {
            "gross_roof_area_m2": round(gross_roof_area, 2),
            "net_usable_area_m2": round(net_usable_area, 2),
            "total_panel_area_m2": round(total_panel_area, 2),
            "ground_coverage_ratio_gcr": round(ground_coverage_ratio, 4),
            "usable_area_utilization": round(usable_area_utilization, 4),
            "average_solar_access": round(avg_solar_access, 4),
            "min_solar_access_threshold": self.constraint_rules.min_solar_access,
            "reserved_space_ratio": self.constraint_rules.reserved_space_ratio,
            "calculated_pitch_m": round(step_y, 3),
            "execution_time_seconds": round(elapsed_sec, 4),
        }

        return PlacementResult(
            panel_coordinates=panel_coords_array,
            total_panel_count=total_count,
            installed_dc_capacity_kwp=installed_kwp,
            panel_polygons=placed_panels,
            net_usable_polygon=net_domain,
            roof_polygon=roof_poly,
            obstacle_polygons=obstacle_polys,
            solar_access_scores=placed_scores,
            panel_spec=self.panel_spec,
            constraint_rules=self.constraint_rules,
            metrics=metrics,
        )

    def _empty_result(
        self,
        roof_poly: Union[Polygon, MultiPolygon],
        obstacle_polys: List[Polygon],
        net_domain: Union[Polygon, MultiPolygon],
        start_time: float,
    ) -> PlacementResult:
        """Return a structured empty placement result when no usable area exists."""
        return PlacementResult(
            panel_coordinates=np.empty((0, 4, 2), dtype=np.float64),
            total_panel_count=0,
            installed_dc_capacity_kwp=0.0,
            panel_polygons=[],
            net_usable_polygon=net_domain,
            roof_polygon=roof_poly,
            obstacle_polygons=obstacle_polys,
            solar_access_scores=np.empty(0, dtype=np.float64),
            panel_spec=self.panel_spec,
            constraint_rules=self.constraint_rules,
            metrics={
                "gross_roof_area_m2": round(float(roof_poly.area), 2) if not roof_poly.is_empty else 0.0,
                "net_usable_area_m2": 0.0,
                "total_panel_area_m2": 0.0,
                "execution_time_seconds": round(time.perf_counter() - start_time, 4),
            },
        )


# ============================================================================
# Main Entry Point Function
# ============================================================================

def optimize_panel_placement(
    roof_polygons: Union[Polygon, MultiPolygon, Sequence[Any], Dict[str, Any]],
    obstacle_polygons: Union[Sequence[Any], Polygon, MultiPolygon, None] = None,
    solar_access_matrix: Union[SolarAccessMatrix, np.ndarray, Sequence[Sequence[float]], Callable[[float, float], float], float, int, None] = None,
    constraint_rules: Union[ConstraintRules, Dict[str, Any], None] = None,
    panel_spec: Union[PanelSpec, Dict[str, Any], None] = None,
) -> PlacementResult:
    """Top-level entry point for Constraint-Aware Solar Panel Layout Optimization.

    Fits standard PV modules (2.2m x 1.1m) facing South (Azimuth 180°) into clear,
    unshaded roof polygons while enforcing geometric setbacks, obstacle clearances,
    maintenance aisles, and solar access thresholds.

    Parameters:
        roof_polygons: (1) Usable roof polygon(s), coordinates array, or GeoJSON dict.
        obstacle_polygons: (2) Obstacle polygon(s) such as HVAC units, skylights, vents.
        solar_access_matrix: (3) Solar access grid/matrix, 2D array, or callable (minimum 80% threshold).
        constraint_rules: (4) Constraint rules: 1.0m parapet setback, 0.8m aisles, 15% reserved space, etc.
        panel_spec: Optional hardware specs (default 2.2m x 1.1m, 550Wp, 180° Azimuth).

    Returns:
        PlacementResult containing:
            - panel_coordinates: Explicit numpy array of 4 corners (x, y) for every placed panel, shape (N, 4, 2).
            - total_panel_count: Total placed solar panels count.
            - installed_dc_capacity_kwp: Installed DC system capacity in kWp.
            - to_dict() and to_geojson() serialization methods.
    """
    # Parse panel specification
    if panel_spec is None:
        p_spec = PanelSpec()
    elif isinstance(panel_spec, dict):
        p_spec = PanelSpec(**panel_spec)
    elif isinstance(panel_spec, PanelSpec):
        p_spec = panel_spec
    else:
        raise TypeError(f"Invalid panel_spec type: {type(panel_spec)}")

    # Parse constraint rules
    if constraint_rules is None:
        c_rules = ConstraintRules()
    elif isinstance(constraint_rules, dict):
        c_rules = ConstraintRules(**constraint_rules)
    elif isinstance(constraint_rules, ConstraintRules):
        c_rules = constraint_rules
    else:
        raise TypeError(f"Invalid constraint_rules type: {type(constraint_rules)}")

    optimizer = PanelLayoutOptimizer(panel_spec=p_spec, constraint_rules=c_rules)
    return optimizer.optimize_placement(
        roof_input=roof_polygons,
        obstacles_input=obstacle_polygons,
        solar_access_input=solar_access_matrix,
    )


# ============================================================================
# Publication-Quality Visualization
# ============================================================================

def visualize_layout(
    result: PlacementResult,
    solar_access_matrix: Optional[SolarAccessMatrix] = None,
    save_path: Optional[str] = None,
    title: Optional[str] = None,
    show_plot: bool = False,
    figsize: Tuple[int, int] = (12, 9),
) -> Any:
    """Generate a rich, publication-grade Matplotlib visualizer for the placed solar layout."""
    import matplotlib.patches as patches
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    fig, ax = plt.subplots(figsize=figsize, dpi=150)
    fig.patch.set_facecolor("#0F172A")  # Dark slate background
    ax.set_facecolor("#1E293B")

    # Plot solar access heatmap background if matrix is available
    if solar_access_matrix is not None and solar_access_matrix.bounds is not None:
        minx, miny, maxx, maxy = solar_access_matrix.bounds
        grid_x = np.linspace(minx, maxx, 150)
        grid_y = np.linspace(miny, maxy, 150)
        gx, gy = np.meshgrid(grid_x, grid_y)
        pts = np.column_stack([gx.ravel(), gy.ravel()])
        z_vals = solar_access_matrix.sample_points(pts).reshape(gx.shape)

        solar_cmap = LinearSegmentedColormap.from_list(
            "solar_access", ["#450A0A", "#78350F", "#D97706", "#FDE047"], N=256
        )
        cax = ax.imshow(
            z_vals,
            extent=(minx, maxx, miny, maxy),
            origin="lower",
            cmap=solar_cmap,
            alpha=0.35,
            interpolation="bicubic",
        )
        cbar = fig.colorbar(cax, ax=ax, fraction=0.035, pad=0.04)
        cbar.set_label("Solar Access Factor", color="#F8FAFC", fontsize=11, fontweight="bold")
        cbar.ax.tick_params(colors="#CBD5E1", labelsize=9)

    # Helper function to plot Shapely polygon
    def _plot_poly(poly: Union[Polygon, MultiPolygon], edge_color, face_color, lw=1.5, ls="-", label=None, zorder=2):
        if poly.is_empty:
            return
        geoms = [poly] if isinstance(poly, Polygon) else poly.geoms
        for idx, g in enumerate(geoms):
            ext_coords = np.array(g.exterior.coords)
            lbl = label if idx == 0 else None
            poly_patch = patches.Polygon(
                ext_coords,
                closed=True,
                edgecolor=edge_color,
                facecolor=face_color,
                linewidth=lw,
                linestyle=ls,
                label=lbl,
                zorder=zorder,
            )
            ax.add_patch(poly_patch)

    # 1. Plot Roof Boundary
    _plot_poly(result.roof_polygon, edge_color="#38BDF8", face_color="#0284C722", lw=2.2, label="Roof Perimeter", zorder=1)

    # 2. Plot Net Usable Domain / Setback boundary
    _plot_poly(result.net_usable_polygon, edge_color="#059669", face_color="#10B98115", lw=1.2, ls="--", label="Net Usable Area", zorder=2)

    # 3. Plot Obstacles
    for idx, obs in enumerate(result.obstacle_polygons):
        _plot_poly(obs, edge_color="#EF4444", face_color="#DC262688", lw=1.5, label="Obstacles" if idx == 0 else None, zorder=4)

    # 4. Plot Placed Solar Panels
    panel_edge = "#60A5FA"
    panel_face = "#1E40AF"
    
    for idx, poly in enumerate(result.panel_polygons):
        ext_coords = np.array(poly.exterior.coords)
        patch = patches.Polygon(
            ext_coords,
            closed=True,
            edgecolor=panel_edge,
            facecolor=panel_face,
            linewidth=0.8,
            alpha=0.92,
            zorder=5,
            label="PV Module (2.2m × 1.1m)" if idx == 0 else None,
        )
        ax.add_patch(patch)

    # Set plot bounds and aesthetics
    if not result.roof_polygon.is_empty:
        rminx, rminy, rmaxx, rmaxy = result.roof_polygon.bounds
        dx = rmaxx - rminx
        dy = rmaxy - rminy
        ax.set_xlim(rminx - 0.08 * dx, rmaxx + 0.08 * dx)
        ax.set_ylim(rminy - 0.08 * dy, rmaxy + 0.08 * dy)

    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linestyle=":", alpha=0.25, color="#94A3B8")
    ax.tick_params(colors="#CBD5E1", labelsize=10)
    for spine in ax.spines.values():
        spine.set_color("#475569")

    ax.set_xlabel("East-West Distance (m)", color="#F8FAFC", fontsize=11, fontweight="bold")
    ax.set_ylabel("North-South Distance (m)", color="#F8FAFC", fontsize=11, fontweight="bold")

    # Header Title & Summary Banner
    plot_title = title or "Constraint-Aware Solar PV Layout Optimization"
    ax.set_title(plot_title, color="#F8FAFC", fontsize=14, fontweight="bold", pad=16)

    # Stats banner in lower left
    info_text = (
        f"Placed Modules: {result.total_panel_count} units\n"
        f"DC Capacity: {result.installed_dc_capacity_kwp:.2f} kWp\n"
        f"Module Size: {result.panel_spec.length}m × {result.panel_spec.width}m ({result.panel_spec.rated_power_w:.0f} Wp)\n"
        f"Azimuth: {result.panel_spec.azimuth_deg:.0f}° (South) | Tilt: {result.panel_spec.tilt_deg:.0f}°\n"
        f"GCR: {result.metrics.get('ground_coverage_ratio_gcr', 0)*100:.1f}% | Usable Area: {result.metrics.get('net_usable_area_m2', 0):.1f} m²"
    )
    props = dict(boxstyle="round,pad=0.6", facecolor="#0F172ACC", edgecolor="#38BDF8", alpha=0.9)
    ax.text(
        0.025,
        0.035,
        info_text,
        transform=ax.transAxes,
        fontsize=9.5,
        color="#F8FAFC",
        verticalalignment="bottom",
        bbox=props,
        fontfamily="monospace",
        zorder=10,
    )

    # Legend
    legend = ax.legend(
        loc="upper right",
        facecolor="#0F172ACC",
        edgecolor="#475569",
        labelcolor="#F8FAFC",
        fontsize=9,
    )
    legend.get_frame().set_alpha(0.85)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())

    if show_plot:
        plt.show()

    return fig, ax
