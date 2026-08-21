# ADR 0004: Treat GOBS as optional enrichment

- **Status:** Accepted
- **Date:** 2026-08-22

## Context

The GOBS website documents state-level compressed CSV files, but its dashboard does not expose a direct raw download. The implemented access path is a request through the official contact form. Making GOBS a mandatory source would therefore place the three-day build on an external response time. The published GOBS field list also does not promise polygon geometry.

Official Google Open Buildings v3 polygons and Open Buildings Temporal v1 height data provide an executable public baseline for the same AOI.

## Decision

Helios will use Google Open Buildings v3 as the default building-geometry source and Open Buildings Temporal v1 as the default height source. A received GOBS state file may enrich candidates with height, floor, land-use and confidence attributes after an audited spatial match.

GOBS fields remain nullable in contracts. Pipeline execution, ranking and the cached demo must work without them. Source availability, match confidence and missingness flow into uncertainty and validation outputs.

## Consequences

- The team does not wait for GOBS access and does not scrape dashboard aggregates.
- Person 1 owns both the access request and the reproducible public fallback.
- Persons 2–4 must support fallback-only and enriched inputs.
- Person 5 exposes optional-source warnings rather than treating absence as failure.
- Person 6 states the exact source mode for every demonstrated run.
- If GOBS arrives, its value is tested through a controlled ablation before it is used in a claim.

See [GOBS access finding and executable fallback](../../data/GOBS_ACCESS_AND_FALLBACK.md) for implementation actions and owner-specific acceptance tests.
