# Helios Human Review and Labeling Rubric

**Version:** `1.0.0`
**Protocol:** `blind-review-v1`
**Owner:** Person 6 (Validation, Evidence, and Demo Owner)
**Applicable Scope:** Kharghar Area of Interest (`kharghar-v1`) and sample test fixtures

---

## 1. Objective and Screening Boundary

Helios is an **early-stage regional rooftop solar screening and inspection prioritization platform**. It identifies candidate buildings worth sending human surveyors to inspect first.

> [!IMPORTANT]
> **Helios is not an engineering, structural, legal, or utility interconnection approval system.**
> - A decision of `inspect` means: *"This building exhibits strong preliminary visual/spatial characteristics and is worth on-site field verification."*
> - A decision of `reject` means: *"This building fails fundamental physical screening constraints (e.g., roof area too small, severe obstruction) and should not consume field surveyor time."*
> - A decision of `uncertain` means: *"Satellite/orthophoto data is ambiguous, conflicting, or incomplete; manual resolution requires on-site audit before rejection or acceptance."*

Reviewers must assign decisions **blindly** without seeing Helios total scores, component ranks, scenario weights, or MCDA outputs.

---

## 2. Decision Categories

| Decision | Definition | Actionable Next Step |
|---|---|---|
| `inspect` | The building has clear, unobstructed rooftop area, viable access, and presents a high-priority candidate for solar deployment. | Assign to field inspection team for structural and electrical audit. |
| `uncertain` | Rooftop characteristics are ambiguous due to low image resolution, tree overhang, complex roof geometry, or missing height data. | Flag for secondary analyst review or ground-level drive-by verification. |
| `reject` | The candidate fails minimum viability criteria (e.g., footprint $< 40\text{ m}^2$, rooftop fully obstructed by HVAC/water tanks/structures, or demolished). | Exclude candidate from field inspection queue. |

---

## 3. Standardized Reason Code Taxonomy

Reviewers must select one or more standardized reason codes for every evaluation. Custom free-text notes may supplement but cannot replace reason codes.

### Physical and Area Codes
- `strong-roof` / `ample_unobstructed_roof`: Large, flat, contiguous rooftop area free of significant obstructions.
- `area-too-small` / `usable_area_below_minimum`: Estimated usable footprint is under the $40\text{ m}^2$ threshold.
- `complex-geometry`: Highly fragmented, stepped, or non-planar roof structure.

### Shading and Obstruction Codes
- `low-shading` / `minimal_obstruction`: Clear solar exposure with no adjacent taller buildings or dense tree canopy.
- `shading` / `severe_obstruction`: Heavy shadowing from neighboring high-rises, hills, or dense foliage.
- `cluttered-roof`: High density of rooftop infrastructure (mobile towers, water tanks, HVAC units, skylights).

### Access and Grid Proximity Codes
- `good-access`: Direct frontage on paved municipal road enabling equipment transport.
- `poor-access`: Enclosed compound, narrow pedestrian alley, or restricted vehicular access.
- `good-grid`: Proximity to mapped distribution lines / substations within screening limit ($< 2,000\text{ m}$).

### Data and Provenance Confidence Codes
- `verify-height` / `temporal_height_missing`: Building height missing in Temporal v1 raster or requires ground calibration.
- `low-image-resolution`: Satellite or orthophoto imagery lacks sufficient visual sharpness for obstruction assessment.
- `boundary-ambiguity`: S2 tile / building footprint outline does not cleanly align with visible structure.
- `economics-good`: Indicative yield-to-cost or commercial viability proxy appears favorable.
- `rent-missing`: Roof rental/lease benchmark data not available in public records.

---

## 4. Allowable Reviewer Evidence

Reviewers may inspect only the following baseline evidence layers:
1. High-resolution orthophoto / satellite base imagery.
2. Building polygon footprint boundary from Open Buildings v3.
3. Copernicus GLO-30 digital elevation model (terrain slope context).
4. Temporal v1 2023 building height raster and presence score.
5. OpenStreetMap road network and mapped power infrastructure.

> [!CAUTION]
> **Strict Anti-Bias Rule:** Reviewers must NEVER view or reference:
> - Helios balanced, energy-first, or cost-first ranking scores.
> - MCDA rank position (e.g., Rank 1 vs Rank 5).
> - Ranking stability reports or CCRA acceptability probabilities.

---

## 5. Examples and Counterexamples

### Example 1: `inspect`
- **Visual evidence:** Rectangular commercial building, clear concrete flat roof ($> 150\text{ m}^2$), height $15\text{ m}$, paved road frontage, no taller buildings within $50\text{ m}$.
- **Decision:** `inspect`
- **Reason codes:** `["strong-roof", "good-access", "low-shading"]`
- **Notes:** High-confidence flat roof with excellent road access.

### Example 2: `uncertain`
- **Visual evidence:** Residential apartment building ($120\text{ m}^2$) with partial shade from adjacent tree line; Temporal v1 height missing or low confidence ($0.42$).
- **Decision:** `uncertain`
- **Reason codes:** `["verify-height", "shading", "economics-good"]`
- **Notes:** Good building size but requires ground height measurement and shadow verification.

### Example 3: `reject`
- **Visual evidence:** Small tin-shed structure ($25\text{ m}^2$) located in dense alleyway with adjacent $8$-story building blocking southern sky.
- **Decision:** `reject`
- **Reason codes:** `["area-too-small", "shading", "poor-access"]`
- **Notes:** Area below $40\text{ m}^2$ threshold and severe southern obstruction.

---

## 6. Review Workflow and Data Entry

1. Open blind review table or GeoLibre field validation form.
2. Load candidate by `candidate_id`.
3. Record `started_at` timestamp.
4. Inspect allowed visual and spatial evidence layers.
5. Select `decision` (`inspect`, `uncertain`, or `reject`).
6. Tag applicable `reason_codes`.
7. Add optional explanatory `notes`.
8. Record `reviewed_at` timestamp.
9. Save and commit label to `data/sample/validation/validation_labels.csv`.
