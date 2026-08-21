"""Export the versioned Person 4 request and output JSON Schemas."""

from __future__ import annotations

import json
from pathlib import Path

from helios.ranking.contracts import P5RankingRequest, RankingBundle

SCHEMA_DIR = Path("docs/person4/schemas")


def main() -> None:
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    schemas = {
        "person4-request.schema.json": P5RankingRequest.model_json_schema(),
        "person4-output.schema.json": RankingBundle.model_json_schema(),
    }
    for name, schema in schemas.items():
        path = SCHEMA_DIR / name
        path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
        print(path)


if __name__ == "__main__":
    main()
