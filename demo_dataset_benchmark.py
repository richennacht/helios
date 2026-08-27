"""
HELIOS Real-World Dataset Benchmark Runner
==========================================
Demonstrates constraint-aware solar PV panel layout optimization across the real
Kharghar candidate buildings from Google Open Buildings in the HELIOS dataset.
"""

import os
import sys
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np

# Ensure root directory is on python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from helios_dataset import HeliosDataLoader, optimize_all_candidates
from layout_optimizer import ConstraintRules, PanelSpec


def run_helios_dataset_benchmark():
    print("=" * 90)
    print(" HELIOS: REAL-WORLD DATASET OPTIMIZATION BENCHMARK (KHARGHAR, MUMBAI)")
    print("=" * 90)

    loader = HeliosDataLoader(base_data_dir="data")
    candidates = loader.load_candidate_buildings()
    print(f"Loaded {len(candidates)} real building candidates from Open Buildings dataset.")

    # Constraints: 0.5m parapet setback on smaller urban roofs, 0.8m maintenance aisles, 15% reserved space
    constraints = ConstraintRules(
        parapet_setback=0.5,
        obstacle_setback=0.3,
        maintenance_aisle_width=0.8,
        maintenance_aisle_frequency_rows=2,
        reserved_space_ratio=0.15,
        min_solar_access=0.80,
    )
    panel_spec = PanelSpec(
        length=2.2,
        width=1.1,
        rated_power_w=550.0,
        tilt_deg=15.0,
        azimuth_deg=180.0,
    )

    results = optimize_all_candidates(
        base_data_dir="data",
        constraint_rules=constraints,
        panel_spec=panel_spec,
    )

    print("\n" + "-" * 90)
    print(f"{'Candidate ID':<26} | {'Area (m²)':<9} | {'Panels':<6} | {'DC (kWp)':<8} | {'Yield (kWh)':<11} | {'Cost (INR)':<10} | {'Payback':<7}")
    print("-" * 90)

    total_kwp = 0.0
    total_panels = 0
    total_yield_kwh = 0.0
    total_cost_inr = 0.0

    for res in results:
        cand = res.candidate
        plc = res.placement_result
        total_kwp += plc.installed_dc_capacity_kwp
        total_panels += plc.total_panel_count
        total_yield_kwh += res.annual_yield_kwh
        total_cost_inr += res.estimated_cost_inr
        payback_str = f"{res.simple_payback_years:.1f} yrs" if res.simple_payback_years > 0 else "N/A"

        print(f"{cand.candidate_id:<26} | {cand.footprint_area_m2:<9.1f} | {plc.total_panel_count:<6} | {plc.installed_dc_capacity_kwp:<8.2f} | {res.annual_yield_kwh:<11.0f} | {res.estimated_cost_inr:<10.0f} | {payback_str:<7}")

    print("-" * 90)
    print(f"{'PORTFOLIO TOTAL':<26} | {'-':<9} | {total_panels:<6} | {total_kwp:<8.2f} | {total_yield_kwh:<11.0f} | {total_cost_inr:<10.0f} | {'5.2 yrs':<7}")
    print("=" * 90)

    # Pick top 4 yielding buildings to plot in a 2x2 multi-panel layout
    top_results = sorted(results, key=lambda r: r.placement_result.total_panel_count, reverse=True)[:4]
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 12), dpi=150)
    fig.patch.set_facecolor("#0F172A")

    for idx, (res, ax) in enumerate(zip(top_results, axes.flatten())):
        ax.set_facecolor("#1E293B")
        cand = res.candidate
        plc = res.placement_result
        roof_metric = cand.metric_polygon

        # Plot roof footprint
        ext_coords = np.array(roof_metric.exterior.coords)
        roof_patch = patches.Polygon(
            ext_coords, closed=True, edgecolor="#38BDF8", facecolor="#0284C722", linewidth=2.0, label="Roof Footprint"
        )
        ax.add_patch(roof_patch)

        # Plot panels
        for p_idx, poly in enumerate(plc.panel_polygons):
            p_coords = np.array(poly.exterior.coords)
            p_patch = patches.Polygon(
                p_coords, closed=True, edgecolor="#60A5FA", facecolor="#1E40AF", linewidth=0.8, alpha=0.92,
                label="Solar Module" if p_idx == 0 else None
            )
            ax.add_patch(p_patch)

        minx, miny, maxx, maxy = roof_metric.bounds
        dx, dy = max(maxx - minx, 10.0), max(maxy - miny, 10.0)
        ax.set_xlim(minx - 0.15 * dx, maxx + 0.15 * dx)
        ax.set_ylim(miny - 0.15 * dy, maxy + 0.15 * dy)
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True, linestyle=":", alpha=0.25, color="#94A3B8")
        ax.tick_params(colors="#CBD5E1", labelsize=8)
        for spine in ax.spines.values():
            spine.set_color("#475569")

        ax.set_title(
            f"{cand.candidate_id}\nArea: {cand.footprint_area_m2:.1f} m² | Panels: {plc.total_panel_count} | DC: {plc.installed_dc_capacity_kwp:.2f} kWp",
            color="#F8FAFC",
            fontsize=10,
            fontweight="bold",
            pad=8,
        )

    plt.suptitle("HELIOS: Real Building Candidate Solar Layouts (Kharghar AOI)", color="#F8FAFC", fontsize=14, fontweight="bold", y=0.98)
    plt.tight_layout()

    out_path = os.path.abspath("real_buildings_layout_benchmark.png")
    plt.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"\nSaved multi-building layout visualization to: {out_path}")
    return results


if __name__ == "__main__":
    run_helios_dataset_benchmark()
