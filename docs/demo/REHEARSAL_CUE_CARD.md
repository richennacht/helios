# Helios Presenter Rehearsal Cue Card

**Target Time:** 4:00 minutes (240s) | **Max Allowed:** 5:00 minutes (300s)
**Presenter:** Person 6 (Validation & Demo Lead)

---

## â±ï¸ Timeline Milestones & Key Soundbites

```text
[0:00 - 0:30] PROBLEM
Soundbite: "Helios solves the commercial solar discovery bottleneck: finding viable rooftops before sending field crews."
Key Phrase: "Inspection prioritization, not EPC design."

[0:30 - 1:00] PROVENANCE & KHARGHAR AOI
Soundbite: "Open Buildings v3 + Temporal v1 public baseline with signed manifest provenance."
Key Phrase: "GOBS is request-only optional enrichment; public baseline operates lawfully today."

[1:00 - 1:30] RUN EXECUTION & HARD FILTERS
Soundbite: "Hard exclusions eliminate roofs <40 m2 or beyond grid limits before scoring."
Key Phrase: "Multi-Criteria Decision Analysis (MCDA) normalizes criteria within the run."

[1:30 - 2:15] CANDIDATE DETAIL & STABILITY (roof-a & roof-b)
Soundbite: "roof-a: Score 0.884, 100% stability probability under 1,000 Monte Carlo draws."
Soundbite: "roof-b: 70.8% retention; flagged as 'review required' so surveyors know when to verify."

[2:15 - 2:45] SCENARIO RERANKING
Soundbite: "Instant reranking between Balanced and Energy-First presets without recomputing physics."

[2:45 - 3:20] EVALUATION VS. MANUAL BASELINE
Soundbite: "7x faster (4m vs 28m), nDCG@2 0.8066 vs 0.3066 (+0.5000), Precision@2 0.50 vs 0.0."
Soundbite: "Manual scouting picked heavily shaded roof-e; Helios correctly filtered it."

[3:20 - 3:45] LIMITATIONS & BOUNDARY
Soundbite: "Does NOT replace structural audits, shadow analysis, single-line diagrams, or grid permits."

[3:45 - 4:00] CLOSE & TECHNICAL HANDOFF
Soundbite: "Reproducible, physics-informed, and transparent. Opening to questions for Persons 1â€“5."
```

---

## ðŸš¨ Emergency Fallback Protocols

| Problem | Approved Presenter Response | Action |
|---|---|---|
| **Internet / Tile Failure** | *"Switching to our local offline cache in GeoLibre."* | Switch to local vector polygons and Copernicus DEM hillshade. |
| **FastAPI Backend Timeout** | *"Demonstrating from our pre-computed Kharghar run bundle."* | Open `data/fixtures/person4/person4-request.json` output bundle. |
| **Judge asks: 'Why not use deep learning for ranking?'** | *"MCDA provides deterministic, explainable rankings out-of-the-box. ML is an optional challenger evaluated only when sufficient held-out human labels exist."* | Route architecture details to Person 4. |
| **Judge asks for an unmeasured number** | *"That metric was not in our frozen evaluation scope; we report only verified evidence from our ledger."* | Never guess or extrapolate live. |

---

## ðŸŽ¯ Technical Escalation Roster

- **GIS Data, Open Buildings, GOBS Status, Copernicus DEM:** $\rightarrow$ **Person 1**
- **Spatial Geometry, Road Distance, Grid Proximity, Height Fusion:** $\rightarrow$ **Person 2**
- **pvlib Solar Yield, Shading Losses, Capex/Rent Proxies:** $\rightarrow$ **Person 3**
- **MCDA Scoring, CCRA Stability, Explanations, Evaluation Metrics:** $\rightarrow$ **Person 4**
- **FastAPI Routes, PostGIS Schemas, Pipeline Orchestration, Docker:** $\rightarrow$ **Person 5**
