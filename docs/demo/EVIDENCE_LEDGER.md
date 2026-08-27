# Presentation and Demonstration Evidence Ledger

**Version:** `1.0.0`
**Status:** AUDITED AND LOCKED
**Date:** 2026-08-22
**Owner:** Person 6 (Validation, Evidence, and Demo Owner)

---

## 1. Traceability Policy

Every quantitative statement, percentage, ranking metric, or comparison presented in the Helios slide deck, demonstration, or documentation **must trace to an exact recorded run, metric, sample size, date, and repository evidence file**.

> [!IMPORTANT]
> **Core Integrity Rules:**
> 1. Never fabricate or extrapolate metrics beyond what is recorded in checked-in fixtures.
> 2. Use the word *"improved"* only when a stored evaluation run beats a named baseline on a named metric. Otherwise, use *"designed to improve"*.
> 3. Mark unsupported claims as `BLOCKED`.

---

## 2. Evidence Register

| Claim ID | Slide / Context | Exact Claim Wording | Metric | Measured Value | $K$ | Sample Size | Run ID / Version | Evidence Source | Status |
|---|---|---|---|---|---|---|---|---|---|
| `claim-01` | Slide 5 (Evaluation) | *"Helios reduced time to shortlist from 28.0 minutes to 4.0 minutes (7x faster) compared to manual scouting on the test fixture."* | `shortlist_minutes_delta` | `-24.0 min` ($4.0$ vs $28.0$) | 2 | 5 candidates | `kharghar-person4-demo-v1` | `data/fixtures/person4/person4-request.json` | **VERIFIED** |
| `claim-02` | Slide 5 (Evaluation) | *"Helios balanced MCDA achieved nDCG@2 of 0.8066 vs 0.3066 for manual scouting (+0.5000 rank quality gain)."* | `ndcg_at_k_delta` | `+0.5000` ($0.8066$ vs $0.3066$) | 2 | 5 candidates | `kharghar-person4-demo-v1` | `data/fixtures/person4/person4-request.json` | **VERIFIED** |
| `claim-03` | Slide 5 (Evaluation) | *"Helios balanced MCDA achieved Precision@2 of 0.50 (1/2 inspect) compared to 0.0 (0/2 inspect) for manual scouting."* | `precision_at_k_delta` | `+0.50` ($0.50$ vs $0.0$) | 2 | 5 candidates | `kharghar-person4-demo-v1` | `data/fixtures/person4/person4-request.json` | **VERIFIED** |
| `claim-04` | Slide 4 (Stability) | *"Top candidate roof-a achieved 100% top-2 retention probability across 1,000 Monte Carlo uncertainty iterations in CCRA-v1."* | `probability_top_k` | `1.0` ($100\%$) | 2 | 1,000 draws | `ccra-v1` | `data/fixtures/person4/person4-request.json` | **VERIFIED** |
| `claim-05` | Slide 4 (Explainability) | *"Candidate roof-b required human review due to sensitivity under weight/feature perturbation (70.8% top-2 probability, rank interval 2-3)."* | `probability_top_k` | `0.708` ($70.8\%$) | 2 | 1,000 draws | `ccra-v1` | `data/fixtures/person4/person4-request.json` | **VERIFIED** |
| `claim-06` | Slide 2 (Data & Provenance) | *"Kharghar baseline public fixture provides 15 Open Buildings v3 candidate polygons with 13 positive Temporal v1 height observations (86.7% coverage)."* | `height_coverage_fraction` | `0.867` ($13/15$) | N/A | 15 buildings | `kharghar-v1` | `docs/data/DATA_AND_PROVENANCE.md` | **VERIFIED** |
| `claim-07` | Slide 2 (Data Access) | *"GOBS Maharashtra state file is request-only; system operates seamlessly on Open Buildings v3 public fallback without blocking."* | `gobs_enrichment_status` | `optional_fallback_active` | N/A | N/A | `gobs-finding-2026-08-22` | `docs/data/GOBS_ACCESS_AND_FALLBACK.md` | **VERIFIED** |
| `claim-08` | Slide 6 (Limitations) | *"Helios is designed to prioritize field inspections and does NOT replace structural, electrical, legal, or grid interconnection approvals."* | `screening_boundary_compliance` | `100% compliant` | N/A | N/A | `architecture-v1` | `README.md` | **VERIFIED** |
| `claim-09` | Unapproved | *"General regional solar potential improvement across entire metropolitan Mumbai."* | `metropolitan_general_accuracy` | `BLOCKED` | N/A | N/A | `unsupported` | `NONE` | **BLOCKED** |

---

## 3. Audit Commands for Verification

To reproduce and verify the evaluation claims in the ledger, execute:

```powershell
.\.venv\Scripts\python.exe scripts\run_person4.py data\fixtures\person4\person4-request.json
```

Inspect the returned JSON `evaluation_report` and `stability_report` sections:
- `evaluation_report.deltas.shortlist_minutes == -24.0`
- `evaluation_report.deltas.ndcg_at_k == 0.5`
- `evaluation_report.deltas.precision_at_k == 0.5`
- `stability_report.candidates[0].probability_top_k == 1.0` (`roof-a`)
- `stability_report.candidates[1].probability_top_k == 0.708` (`roof-b`)
