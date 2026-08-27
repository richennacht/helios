# Three-day hackathon runbook

## Day 1 — make one candidate real

### Hours 0–2

- clone, install, run CI locally;
- freeze Kharghar AOI, CRS and reference date;
- register source manifests and agree on units;
- submit the GOBS Maharashtra state-file request, record it as optional, and begin the Google Open Buildings v3 plus Temporal v1 fallback immediately;
- Person 5 freezes contracts and sample fixtures;
- Persons 2–4 begin from fixtures while Person 1 acquires real data;
- Person 6 prepares the blind validation rubric and manual-baseline sheet.

### Hours 2–12

- Person 1 publishes Kharghar Open Buildings candidates, sampled Temporal heights, context layers and manifests; GOBS enriches them only if received and audited;
- Person 2 produces spatial, height and proximity features;
- Person 3 produces solar-yield and economic features;
- Person 4 produces eligibility, score, rank and stability output;
- Person 5 joins, persists and serves the candidate through the API;
- Person 6 records the candidate review and baseline procedure.

**Gate:** one real candidate completes the entire path before bulk processing begins.

## Day 2 — scale and prove

- scale to 1,000–5,000 candidates in the frozen AOI;
- Person 1 freezes the real data package;
- Persons 2 and 3 run their independent batch feature stages;
- Person 4 adds batch normalization, baselines and stability simulation;
- Person 5 runs the integrated pipeline and fixes contract/runtime failures;
- Person 6 reviews a defensible sample and records manual-baseline timing;
- Person 1 styles the GeoLibre shortlist, confidence and exclusion layers using Person 5 output;
- fix performance and data-quality failures before adding features.

**Gate:** stored metrics for at least one baseline comparison and a repeatable top-K map.

## Day 3 — harden and present

- freeze features by midday;
- run a clean environment setup and full test suite;
- capture source/provenance view, scenario rerank and candidate explanation;
- rehearse the same AOI and pre-cache permissible data;
- merge only demo-critical fixes after freeze.

## Demo sequence

1. Select AOI and balanced scenario.
2. Show sources, reference date and warnings.
3. Run analysis and display ranked roofs.
4. Open one candidate: raw metrics, five components, confidence, reasons and cautions.
5. Change scenario weights and show transparent reranking.
6. Compare Helios top-K with the manual or solar-only baseline.
7. State the screening boundary and required field/engineering checks.

## Failure fallbacks

- Keep one small sample request and GeoJSON in the repository.
- Cache only redistributable inputs.
- If GOBS is unavailable, run the documented Open Buildings v3/Temporal v1 baseline and show the optional-source warning; do not scrape dashboard aggregates.
- If a live data endpoint fails, demonstrate the recorded source version and manifest.
- If ML challenger fails, use the deterministic baseline; never hide the result.
