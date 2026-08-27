"""
HELIOS - Constraint-Aware Solar PV Panel Layout Optimizer & Dataset Integration
"""

from helios_dataset import (
    BuildingCandidate,
    BuildingPVResult,
    HeliosDataLoader,
    latlon_to_local_meters,
    local_meters_to_latlon,
    optimize_all_candidates,
    optimize_building_pv,
    project_polygon_to_latlon,
    project_polygon_to_meters,
)
from layout_optimizer import (
    ConstraintRules,
    PanelLayoutOptimizer,
    PanelSpec,
    PlacementResult,
    SolarAccessMatrix,
    optimize_panel_placement,
    visualize_layout,
)

__all__ = [
    "optimize_panel_placement",
    "PanelSpec",
    "ConstraintRules",
    "SolarAccessMatrix",
    "PlacementResult",
    "PanelLayoutOptimizer",
    "visualize_layout",
    "HeliosDataLoader",
    "BuildingCandidate",
    "BuildingPVResult",
    "optimize_building_pv",
    "optimize_all_candidates",
    "latlon_to_local_meters",
    "local_meters_to_latlon",
    "project_polygon_to_meters",
    "project_polygon_to_latlon",
]

__version__ = "1.0.0"
