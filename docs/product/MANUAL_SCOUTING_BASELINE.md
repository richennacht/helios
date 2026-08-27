# Manual Scouting Baseline Protocol

**Protocol Identifier:** `manual-scout-v1`
**Version:** `1.0.0`
**Status:** FROZEN BEFORE HELIOS RANKINGS REVEALED
**Date:** 2026-08-22
**Owner:** Person 6 (Validation, Evidence, and Demo Owner)
**Target AOI:** Kharghar Region (`kharghar-v1`)

---

## 1. Context and Purpose

To objectively evaluate whether Helios improves solar scouting efficiency and shortlist quality, the team established a controlled **manual scouting baseline** prior to viewing any automated Helios rankings.

This document formally records the traditional manual scouting protocol, tools, time budgets, selection rules, and execution outcomes.

---

## 2. Experimental Parameters

| Parameter | Specification |
|---|---|
| **Area of Interest (AOI)** | Kharghar (`kharghar-v1`), Navi Mumbai |
| **Protocol Version** | `manual-scout-v1` |
| **Analyst Time Budget** | 30 minutes maximum (completed in 28.0 minutes) |
| **Selection Target ($K$)** | Top $K=2$ to $4$ candidate rooftops |
| **Ground Truth Label Set** | `blind-review-v1` (blind human labels) |
| **Stopping Rule** | Expiration of 30-minute timer OR completion of shortlist |

---

## 3. Allowed vs. Disallowed Tools

### Allowed Tools (Traditional Workflow)
- Standard GIS desktop viewer (e.g., GeoLibre / QGIS) loaded with satellite orthophoto and OpenStreetMap base layers.
- Manual distance measuring and bounding-box area estimation tools.
- Manual spreadsheet for logging candidate coordinates, IDs, notes, and elapsed time.

### Disallowed Tools (Helios Safeguards)
- NO access to Helios automated ranking tables or composite scores.
- NO access to pre-computed pvlib annual solar-yield layers.
- NO access to MCDA scenario weights (balanced, energy-first, cost-first).
- NO access to CCRA stability probabilities or rank acceptability metrics.

---

## 4. Manual Scouting Execution Sequence

1. **Timer Start ($t = 0\text{ min}$):** Analyst opens unranked candidate map of Kharghar.
2. **Visual Panning:** Analyst manually pans across satellite tiles to visually identify large rooftops.
3. **Manual Area Estimation:** Analyst clicks polygon vertices to measure rough roof dimensions.
4. **Context Check:** Analyst visually scans adjacent buildings for obvious height disparities.
5. **Selection Logging:** Analyst records candidate ID, timestamp, and qualitative rationale in `data/sample/validation/manual_baseline.csv`.
6. **Stopping Point ($t = 28\text{ min}$):** Analyst concludes search upon selecting 4 candidate roofs.

---

## 5. Recorded Manual Selections

| Order | Candidate ID | Selection Timestamp | Elapsed (min) | Initial Analyst Impression | Blind Ground Truth (`blind-review-v1`) |
|---|---|---|---|---|---|
| 1 | `roof-b` | 2026-08-22T10:08:00Z | 8.0 min | Medium flat roof, looks clean from satellite | `uncertain` (`economics-good`) |
| 2 | `roof-e` | 2026-08-22T10:17:00Z | 17.0 min | Large footprint rooftop | `reject` (`shading`, `rent-missing`) |
| 3 | `roof-a` | 2026-08-22T10:24:00Z | 24.0 min | Clear flat commercial roof | `inspect` (`strong-roof`, `good-access`) |
| 4 | `roof-c` | 2026-08-22T10:28:00Z | 28.0 min | Apparent good solar exposure | `inspect` (`yield-good`, `verify-height`) |

---

## 6. Baseline Performance Comparison Summary

When evaluated against the locked blind review labels (`blind-review-v1` with $K=2$):

| Metric | Manual Scouting Baseline | Helios Balanced MCDA | Delta / Improvement |
|---|---|---|---|
| **Time to Shortlist** | 28.0 minutes | 4.0 minutes | **-24.0 minutes (7x faster)** |
| **Precision@2** | 0.0 (0/2 `inspect`) | 0.50 (1/2 `inspect`) | **+0.50** |
| **Recall@2** | 0.0 (0/2 `inspect`) | 0.50 (1/2 `inspect`) | **+0.50** |
| **nDCG@2** | 0.3066 | 0.8066 | **+0.5000** |

### Why Manual Scouting Failed on Top-2:
- Manual visual inspection selected `roof-e` due to large apparent footprint, but failed to detect severe localized shading and missing rent proxies.
- Manual scouting chose `roof-b` first due to visual prominence, but roof required height verification.
- Helios placed `roof-a` at Rank 1, properly accounting for yield, road access, grid proximity, and low shading.

---

## 7. Anti-Bias and Reproducibility Protocol

- The selection order was locked and committed to version control before revealing Helios ranking bundles.
- Candidate IDs are preserved exactly across P1, P2, P3, P4, P5, and P6 artifacts.
- No retrospective modifications to selection order, elapsed times, or protocol definitions are permitted.
