"""Run the isolated Person 4 ranking bundle from a JSON request."""

from __future__ import annotations

import argparse
from pathlib import Path

from helios.ranking.contracts import P5RankingRequest
from helios.ranking.engine import rank_candidates


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path, help="P5 person4.v1 request JSON")
    parser.add_argument("--output", type=Path, help="Optional output JSON path")
    args = parser.parse_args()

    request = P5RankingRequest.model_validate_json(args.request.read_text(encoding="utf-8"))
    output = rank_candidates(request).model_dump_json(indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
        print(args.output)
    else:
        print(output)


if __name__ == "__main__":
    main()
