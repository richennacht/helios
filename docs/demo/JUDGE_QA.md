# Helios Hackathon Judge Q&A Guide

**Role:** Person 6 (Validation, Evidence, and Demo Owner)
**Status:** AUDITED AND DEFENSIBLE
**Guideline:** Provide concise, evidence-backed answers. For deep subsystem implementations, hand off smoothly to the owning engineer.

---

## 1. Data Sources & Provenance

### Q1: "Where do your building footprints and height data come from? What is your dependency on GOBS?"
- **Defensible Answer:**
  > *"Helios utilizes **Google Open Buildings v3** for building polygon footprints and **Open Buildings Temporal v1 (2023)** sampled at building centroids for height and presence observations. All datasets are registered with licenses, dates, and SHA-256 checksums in our source manifests.*
  >
  > *Regarding GOBS (Grid-connected Open Buildings Solar): our verified access audit confirmed that state-level CSV files are request-only via official channels, not a direct public download API. Consequently, Helios executes cleanly on our reproducible Open Buildings public baseline. A GOBS state file is treated as optional enrichment that adds confidence when available, but never blocks pipeline execution."*
- **Technical Lead:** **Person 1 (Data & GIS Engineer)**

---

## 2. Novelty & Technical Contribution

### Q2: "What is technically novel about Helios compared to existing solar map portals?"
- **Defensible Answer:**
  > *"Existing portals either provide coarse regional heatmaps without building-level geometry or act as black-box calculators. Helios introduces three core innovations:*
  > 1. ***Late Modular Fusion:** Decoupling spatial GIS processing, physics-based pvlib modeling, and multi-criteria scoring.*
  > 2. ***Confidence-Calibrated Rank Acceptability (CCRA-v1):** Sizing Monte Carlo rank stability intervals from data uncertainty rather than rewarding candidates for having more observed fields.*
  > 3. ***Deterministic Explainability:** Emitting auditable mathematical traces and human-readable reason codes without generative AI hallucinations."*
- **Technical Lead:** **Person 4 (Ranking & ML Engineer)**

---

## 3. Accuracy & Ground Truth Validation

### Q3: "How do you prove Helios actually works? What is your validation accuracy?"
- **Defensible Answer:**
  > *"We conducted a controlled blind human validation (`blind-review-v1`) with independent orthophoto review using a standardized rubric (`inspect`, `uncertain`, `reject`). Evaluated against our pre-frozen manual scouting baseline (`manual-scout-v1`):*
  > - *Helios reduced scouting time from **28.0 minutes to 4.0 minutes** (a 7x speedup).*
  > - *Helios achieved an **nDCG@2 of 0.8066 vs 0.3066** for manual scouting (+0.5000 rank gain).*
  > - *Helios achieved a **Precision@2 of 0.50 vs 0.0**, correctly filtering an unviable, heavily shaded roof (`roof-e`) that manual visual inspection mistakenly selected.*
  >
  > *We report these metrics honestly as hackathon sample evidence, without exaggerating general metropolitan accuracy."*
- **Technical Lead:** **Person 6 (Validation Owner) & Person 4 (Evaluation Lead)**

---

## 4. Why is Machine Learning Optional?

### Q4: "Why did you choose MCDA rather than training an end-to-end Deep Learning / Graph Neural Network ranker?"
- **Defensible Answer:**
  > *"In municipal and commercial solar development, developers require auditable, legally defensible justifications for why site A is prioritized over site B. Black-box neural rankers cannot guarantee monotonicity across physical constraints and hallucinate explanations.*
  >
  > *Multi-Criteria Decision Analysis (MCDA) provides deterministic, instantaneous scenario reranking with complete mathematical traceability. In our architecture (ADR 0003), ML is structured as an **optional challenger model**â€”it is only promoted if it demonstrably beats deterministic MCDA on held-out human validation labels while maintaining explainability."*
- **Technical Lead:** **Person 4 (Ranking & ML Engineer)**

---

## 5. System Limitations & Screening Boundary

### Q5: "Can a solar developer use Helios to immediately install solar panels without a site visit?"
- **Defensible Answer:**
  > *"Absolutely not, and our documentation enforces this strict product boundary:*
  > - *Helios is an **inspection prioritization tool**, not an EPC engineering software.*
  > - *It does NOT replace on-site structural load testing, parapet inspection, micro-shade pyranometer measurements, electrical single-line diagram design, DISCOM grid interconnection studies, or building ownership lease negotiations.*
  > - *It ensures field survey teams spend time on the top 5% of viable buildings rather than wasting days on unsuitable roofs."*
- **Technical Lead:** **Person 6 (Product & Validation Lead)**

---

## 6. Grid Proximity vs. Hosting Capacity

### Q6: "Does your grid proximity metric prove the local transformer can host the solar capacity?"
- **Defensible Answer:**
  > *"No. Our spatial feature measures Euclidean and network distance (`grid_distance_m`) to mapped distribution substations and power lines from OpenStreetMap. We explicitly document this as a **proximity proxy**, not electrical hosting capacity or thermal substation headroom.*
  >
  > *Detailed hosting capacity requires proprietary DISCOM feeder telemetry, which is outside the public screening boundary."*
- **Technical Lead:** **Person 2 (Spatial Feature Engineer)**

---

## 7. Scalability & System Architecture

### Q7: "How does the architecture scale to an entire state or country?"
- **Defensible Answer:**
  > *"The architecture is modularized into discrete, horizontally scalable stages:*
  > 1. *Data ingestion and spatial feature extraction run as batch workers storing results in PostGIS.*
  > 2. *The FastAPI application handles lightweight ranking requests.*
  > 3. *Scenario reranking takes sub-second latency because normalized feature matrices are cached in memory, requiring only linear algebra weight vector multiplications rather than re-querying GIS layers.*
  >
  > *We have benchmarked the ranking engine to process 5,000 candidate buildings across 1,000 Monte Carlo iterations in under 3 seconds."*
- **Technical Lead:** **Person 5 (Platform Engineer)**

---

## 8. Financial and Commercial Modeling

### Q8: "How reliable are your capex, rent, and payback numbers?"
- **Defensible Answer:**
  > *"Our techno-economic calculations in `helios/features/economics` use standardized, dated benchmark assumptions (e.g., â‚¹45,000/kWp capital cost and â‚¹6.50/kWh commercial tariff for Maharashtra in 2026).*
  >
  > *Where local lease rent benchmarks are unavailable, Helios preserves `null` rather than inserting synthetic zero-rent constants, and propagates a lower economic confidence score to Person 4.*
  >
  > *These outputs provide comparative screening estimates, not bankable financial feasibility models."*
- **Technical Lead:** **Person 3 (Solar & Economics Engineer)**
