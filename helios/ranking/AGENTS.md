# Person 4 ranking instructions

Scope: this directory and its descendants.

- Preserve the `person4.v1` boundary unless a breaking version is explicitly approved.
- Keep hard exclusions separate from preference scoring.
- Keep confidence out of nominal utility; use it only for uncertainty and warnings.
- All score, rank and explanation behavior must be deterministic for a fixed request/seed.
- Runtime explanations must be templates backed by stored fields, never generative prose.
- Do not add a learned ranker to the production path without locked labels, a held-out
  evaluation and an explicit promote/no-promote report.
- Every method assumption must be versioned and returned in the output.
- Add a narrow test before changing ranking, stability or metric semantics.
- Run `python -m pytest tests/test_person4_ranking.py` and Ruff on owned paths.
