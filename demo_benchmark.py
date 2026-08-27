"""
Industrial Benchmark & Visualization Demonstration
===================================================
Demonstrates real-world constraint-aware solar PV panel layout optimization:
- Commercial rooftop with HVAC clusters and skylights
- 1.0m parapet setback, 0.5m obstacle setbacks, 0.8m maintenance aisles
- 15% reserved space policy
- Georeferenced Solar Access Matrix with minimum 80% threshold
- Output: explicit coordinates array, total panel count, and kWp DC capacity
"""

import os
import sys
import numpy as np
from shapely.geometry import Polygon, box

# Add current directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from layout_optimizer import (
    ConstraintRules,
    PanelSpec,
    SolarAccessMatrix,
    optimize_panel_placement,
    visualize_layout,
)


def run_commercial_roof_benchmark():
    print("=" * 80)
    print(" HELIOS: CONSTRAINT-AWARE SOLAR PV PANEL LAYOUT OPTIMIZATION BENCHMARK")
    print("=" * 80)

    # 1. Define Roof Geometry (40m x 25m Commercial Rooftop)
    roof_width, roof_height = 40.0, 25.0
    roof_poly = box(0.0, 0.0, roof_width, roof_height)

    # 2. Define Rooftop Obstacles (HVAC systems, skylights, roof access hatch)
    obstacles = [
        box(6.0, 6.0, 10.0, 10.0),    # Main HVAC Chiller (4m x 4m)
        box(26.0, 14.0, 30.0, 18.0),  # Secondary HVAC Unit (4m x 4m)
        box(16.0, 12.0, 18.0, 14.0),  # Skylight 1 (2m x 2m)
        box(16.0, 6.0, 18.0, 8.0),    # Skylight 2 (2m x 2m)
        box(2.0, 18.0, 4.0, 20.0),    # Roof Access Hatch (2m x 2m)
    ]

    # 3. Create Georeferenced Solar Access Matrix (40m x 25m grid, min 80% threshold)
    # Modeling realistic roof shading: High solar access (92-98%) across central & southern roof,
    # with deep shade near the North parapet wall and behind taller HVAC units.
    nx, ny = 80, 50
    grid_y, grid_x = np.mgrid[0:roof_height:complex(0, ny), 0:roof_width:complex(0, nx)]
    
    # Base high solar access (0.95 = 95%)
    solar_access_grid = np.full((ny, nx), 0.95, dtype=np.float64)

    # Shading gradient along northern edge due to adjacent structure
    north_shade_zone = grid_y > 21.0
    solar_access_grid[north_shade_zone] = 0.50 + 0.35 * (roof_height - grid_y[north_shade_zone]) / 4.0

    # Shading shadow cones behind HVAC units (taller equipment casting North-side shadows)
    for obs in obstacles[:2]: # HVAC units
        cx, cy = obs.centroid.x, obs.centroid.y
        dist_sq = (grid_x - cx)**2 + (grid_y - (cy + 2.5))**2
        shade_mask = np.exp(-dist_sq / 12.0)
        solar_access_grid -= 0.40 * shade_mask

    solar_access_grid = np.clip(solar_access_grid, 0.0, 1.0)
    solar_access = SolarAccessMatrix(data=solar_access_grid, bounds=(0.0, 0.0, roof_width, roof_height))

    # 4. Define Constraint Rules
    constraints = ConstraintRules(
        parapet_setback=1.0,               # 1.0m parapet setback
        obstacle_setback=0.5,              # 0.5m clearance around all equipment
        maintenance_aisle_width=0.8,       # 0.8m maintenance aisles
        maintenance_aisle_frequency_rows=2,# Walkway every 2 module rows
        reserved_space_ratio=0.15,         # 15% reserved space policy
        min_solar_access=0.80,             # Minimum 80% solar access threshold
        optimize_offsets=True,             # Continuous offset grid optimization
    )

    # 5. Define Standard Hardware Specifications (2.2m x 1.1m, 550Wp, 180° Azimuth)
    panel_spec = PanelSpec(
        length=2.2,
        width=1.1,
        rated_power_w=550.0,
        tilt_deg=15.0,
        azimuth_deg=180.0,  # Facing South
        orientation="portrait",
        inter_panel_gap=0.02,
    )

    # 6. Execute Optimization
    print("\nRunning optimize_panel_placement() with constraints:")
    print(f" - Module Dimensions: {panel_spec.length}m × {panel_spec.width}m ({panel_spec.rated_power_w} Wp)")
    print(f" - Azimuth / Tilt: {panel_spec.azimuth_deg}° (South) / {panel_spec.tilt_deg}°")
    print(f" - Parapet Setback: {constraints.parapet_setback}m | Obstacle Clearance: {constraints.obstacle_setback}m")
    print(f" - Maintenance Aisles: {constraints.maintenance_aisle_width}m every {constraints.maintenance_aisle_frequency_rows} rows")
    print(f" - Minimum Solar Access: {constraints.min_solar_access * 100:.0f}%")
    print(f" - Reserved Space Policy: {constraints.reserved_space_ratio * 100:.0f}%")

    result = optimize_panel_placement(
        roof_polygons=roof_poly,
        obstacle_polygons=obstacles,
        solar_access_matrix=solar_access,
        constraint_rules=constraints,
        panel_spec=panel_spec,
    )

    # 7. Print Output Results
    print("\n" + "=" * 80)
    print(" OPTIMIZATION RESULTS SUMMARY")
    print("=" * 80)
    print(f" Total Placed Solar Panels:      {result.total_panel_count} units")
    print(f" Total Installed DC Capacity:    {result.installed_dc_capacity_kwp:.2f} kWp ({result.installed_dc_capacity_kwp * 1000:.0f} Wp)")
    print(f" Explicit Coordinates Array:     Shape {result.panel_coordinates.shape} (N panels, 4 corners, [x, y])")
    print(f" Gross Roof Area:                {result.metrics['gross_roof_area_m2']} m²")
    print(f" Net Usable Area:                {result.metrics['net_usable_area_m2']} m²")
    print(f" Total Module Area:              {result.metrics['total_panel_area_m2']} m²")
    print(f" Ground Coverage Ratio (GCR):    {result.metrics['ground_coverage_ratio_gcr'] * 100:.2f}%")
    print(f" Usable Area Utilization:        {result.metrics['usable_area_utilization'] * 100:.2f}%")
    print(f" Mean Solar Access of Modules:   {result.metrics['average_solar_access'] * 100:.2f}%")
    print(f" Inter-Row Pitch Spacing:        {result.metrics['calculated_pitch_m']} m")
    print(f" Execution Time:                 {result.metrics['execution_time_seconds'] * 1000:.2f} ms")

    # Sample coordinates for first 3 placed panels
    print("\nSample Placed Panel Coordinates (First 3 Panels):")
    for i in range(min(3, result.total_panel_count)):
        coords = result.panel_coordinates[i]
        print(f"  Panel #{i+1}:")
        for corner_idx, pt in enumerate(coords):
            print(f"    Corner {corner_idx+1}: ({pt[0]:.3f}m, {pt[1]:.3f}m)")

    # 8. Render & Save Visualization Plot
    output_image_path = os.path.abspath("solar_layout_benchmark.png")
    print(f"\nGenerating publication-quality visualization -> {output_image_path} ...")
    visualize_layout(
        result=result,
        solar_access_matrix=solar_access,
        save_path=output_image_path,
        title="HELIOS: Constraint-Aware Commercial Solar PV Layout (40m × 25m)",
        show_plot=False,
    )
    print(f"Plot saved successfully to: {output_image_path}")
    print("=" * 80)
    return result


if __name__ == "__main__":
    run_commercial_roof_benchmark()
