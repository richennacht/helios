"""Benchmark the isolated Person 4 pipeline with deterministic synthetic candidates."""

from __future__ import annotations

import argparse
import json
from time import perf_counter

from helios.ranking.contracts import P5RankingRequest
from helios.ranking.engine import rank_candidates


def _request(candidate_count: int, iterations: int) -> P5RankingRequest:
    p2_table = []
    p3_table = []
    confidence_table = []
    for index in range(candidate_count):
        candidate_id = f"benchmark-{index:05d}"
        p2_table.append(
            {
                "candidate_id": candidate_id,
                "geometry": {
                    "type": "Point",
                    "coordinates": [72.8 + (index % 100) * 0.0001, 19.0 + (index // 100) * 0.0001],
                },
                "usable_area_m2": 50 + index % 400,
                "shading_factor": 0.55 + (index % 40) / 100,
                "grid_distance_m": 50 + index % 1800,
                "physical_score": 0.4 + (index % 60) / 100,
                "grid_score": 0.35 + (index % 65) / 100,
                "feature_version": "benchmark-p2-v1",
            }
        )
        p3_table.append(
            {
                "candidate_id": candidate_id,
                "annual_yield_kwh": 8000 + index % 30000,
                "estimated_cost_inr": 400000 + index % 900000,
                "estimated_rent_inr_month": None,
                "generation_score": 0.35 + (index % 65) / 100,
                "economics_score": 0.4 + (index % 60) / 100,
                "assumption_version": "benchmark-p3-v1",
            }
        )
        confidence = 0.45 + (index % 50) / 100
        confidence_table.append(
            {
                "candidate_id": candidate_id,
                "overall_confidence": confidence,
                "criteria": {
                    "generation": confidence,
                    "physical": confidence,
                    "grid": confidence,
                    "economics": confidence,
                },
                "confidence_version": "benchmark-confidence-v1",
            }
        )
    return P5RankingRequest.model_validate(
        {
            "feature_dictionary_version": "person4.features-v1",
            "request_id": f"person4-benchmark-{candidate_count}",
            "assumption_version": "benchmark-p3-v1",
            "scenario": {
                "name": "balanced",
                "minimum_usable_area_m2": 0,
                "maximum_grid_distance_m": None,
                "budget_inr": None,
                "top_k": min(20, candidate_count),
            },
            "robustness": {
                "iterations": iterations,
                "random_seed": 41,
            },
            "p2_table": p2_table,
            "p3_table": p3_table,
            "confidence_table": confidence_table,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=int, default=5000)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--max-seconds", type=float)
    args = parser.parse_args()
    if args.candidates < 1:
        parser.error("--candidates must be at least 1")

    request = _request(args.candidates, args.iterations)
    started = perf_counter()
    bundle = rank_candidates(request)
    elapsed = perf_counter() - started
    result = {
        "candidates": args.candidates,
        "eligible": sum(row.eligible for row in bundle.ranked_candidates),
        "iterations": args.iterations,
        "elapsed_seconds": round(elapsed, 6),
        "candidate_simulations_per_second": round(
            args.candidates * args.iterations / elapsed, 2
        ),
        "feature_dictionary_version": bundle.input_versions["feature_dictionary"],
        "method_version": bundle.stability_report.method_version,
    }
    print(json.dumps(result, indent=2))
    if args.max_seconds is not None and elapsed > args.max_seconds:
        raise SystemExit(
            f"benchmark exceeded limit: {elapsed:.3f}s > {args.max_seconds:.3f}s"
        )


if __name__ == "__main__":
    main()
