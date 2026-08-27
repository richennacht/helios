"""Run the Fuzzy Parameter Project Scheduling ML Challenger from a JSON request."""

from __future__ import annotations

import argparse
from pathlib import Path

from helios.ranking.contracts import P5RankingRequest, RankingMode
from helios.ranking.ml_fuzzy_scheduler import rank_candidates_fuzzy_ml


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path, help="P5 person4.v1 request JSON")
    parser.add_argument("--output", type=Path, help="Optional output JSON path")
    args = parser.parse_args()

    request = P5RankingRequest.model_validate_json(args.request.read_text(encoding="utf-8"))
    # Force FUZZY_ML_CHALLENGER ranking mode
    request_dict = request.model_dump()
    request_dict["ranking_mode"] = RankingMode.FUZZY_ML_CHALLENGER
    ml_request = P5RankingRequest.model_validate(request_dict)

    bundle = rank_candidates_fuzzy_ml(ml_request)
    output_json = bundle.model_dump_json(indent=2)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output_json + "\n", encoding="utf-8")
        print(f"Wrote Fuzzy ML Challenger ranking bundle to {args.output}")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
