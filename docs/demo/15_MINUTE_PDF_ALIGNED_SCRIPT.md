# Helios - 15-minute PDF-aligned presentation script

**Team:** REverb | **Team ID:** SIH26_41  
**Domain:** Regional Solar-Site Discovery and Scouting  
**Format:** Six speakers, approximately 2 minutes 30 seconds each

This script follows the order of the Helios specification: problem and users, literature and gap, proposed solution, technology, differentiation, feasibility and impact. The spoken wording remains close to the team's existing presentation script; the main changes are slide cues and prototype alignment.

## Speaker 1 - Problem, users, and why regional screening matters

**PDF alignment:** Slide 2 - Problem & Users  
**Prototype screen:** Helios landing view, then the regional 3D map

“Good morning. We are Team REverb, and our project is Helios: a regional solar-site discovery and scouting platform.

Solar-site scouting is often carried out one location at a time. Analysts manually inspect imagery, estimate roof size, think about sunlight and shading, check roads and grid access, and then repeat the process for another building. This is slow, inconsistent, and makes it easy to overlook good candidates.

Helios addresses this regional screening problem. Instead of beginning with one known roof, a user selects a region and asks the system to discover and compare candidate rooftops.

Our primary users are developers and EPC teams preparing for site visits, energy analysts comparing candidates using common criteria, and government planners or utilities considering regional constraints such as roads and grid proximity.

The intended decision is simple: which locations should be sent for detailed human and engineering inspection first? Helios is not construction approval. It is a faster, more reproducible pre-screen.”

**Demonstrate:** Open the 3D viewer and explain that it is a review surface for regional candidates, not an engineering drawing.

## Speaker 2 - Literature survey and research gap

**PDF alignment:** Slide 3 - Literature Survey & Existing Solutions  
**Prototype screen:** Candidate Analysis panel and source links

“Existing solutions provide important pieces of this workflow.

Photovoltaic calculators estimate energy production for a selected location and system configuration, but they do not discover and compare all candidate rooftops across a region.

GIS and multi-criteria decision-making methods combine spatial and decision criteria, but many studies begin with a predefined area or a predefined list of alternatives.

Rooftop GIS and machine-learning methods estimate PV potential from building and spatial data, but their results depend strongly on local data quality and validation.

Our research gap is the early regional stage: discover candidates first, then apply technical, infrastructure, and economic screening with an explainable ranking that can be checked against field results.

The Candidate Analysis panel demonstrates this idea. Once a polygon is selected, the user can change the factor being viewed, inspect the gradient, click a ranked building, and see the parameter explanation and source links.”

**Demonstrate:** Select Irradiance or Annual Solar Yield and open the evidence links. State clearly that the current browser values are labelled proxies until the production model is connected.

## Speaker 3 - Proposed solution and GIS workflow

**PDF alignment:** Slide 4 - Proposed Solution: Regional data → candidate detection → spatial and technical screening → economic scoring → ranked shortlist  
**Prototype screen:** 2D polygon selection, then 3D viewer

“The proposed workflow begins with regional data.

The user opens the flat selection map and clicks Draw polygon. They click each corner, then close the polygon either by double-clicking or by clicking the first vertex again. Only the selected region is used for the visible 3D candidate set.

The first processing stage is spatial screening. Helios uses building geometry, roof area, available height data, terrain context, and exclusion rules. Buildings touching or crossing the visual boundary are not shown as selected candidates. Nearby context can still be retained for later shading analysis.

The second stage is solar-potential screening. The intended inputs include irradiance, orientation, slope, and estimated shadow effects.

The output of these stages is a candidate table that can be inspected on the map. The current prototype makes this visible through blue building silhouettes in 2D, selected 3D buildings, rooftop insets, and a color-coded ranking.”

**Demonstrate:** Draw a small polygon, close it by clicking the first vertex, switch to 3D, and show that only buildings inside the selected area are visible.

## Speaker 4 - Decision layer, PV calculation, and ranking

**PDF alignment:** Slide 4 - Solar Potential and Decision Layer  
**Prototype screen:** Candidate Analysis factor selector and clicked candidate

“The decision layer combines technical, infrastructure, and economic indicators so the ranking reflects practical project considerations.

The intended PV calculation estimates production from solar resource, usable area, system assumptions, orientation, slope, and shading. The economic layer is designed to combine indicators such as CAPEX, payback, and LCOE.

Helios uses multi-criteria decision analysis rather than hiding everything inside one opaque number. Criteria are normalized, scenario weights can be changed, and each candidate can show its factor contributions and reason codes.

In the running prototype, the user can select Building Height, Usable Rooftop Area, Irradiance, or Annual Solar Yield. The selected buildings are ranked and recolored across a gradient. Clicking a row locates that building in the 3D view and shows its ID and source.

The current browser irradiance and yield values are transparent proxies. The final version will replace them with the validated PV calculator and research-backed model outputs, while retaining the same user-facing explanation.”

**Demonstrate:** Run two factors, click the top-ranked candidate, and point out that the building ID, color, rooftop inset, and ranking row refer to the same object.

## Speaker 5 - Technology stack and innovation

**PDF alignment:** Slides 5 and 6 - Technology and Innovation / Differentiation  
**Prototype screen:** 2D/3D application and repository architecture

“The technology stack separates geospatial processing from decision analytics.

The data layer is designed for satellite or aerial imagery, solar and weather data, digital elevation models, building footprints, roads, and grid layers.

The geospatial layer uses Python GIS tools such as GeoPandas, Rasterio, Shapely or GDAL, with PostGIS as the scaling direction for spatial storage and queries.

The analytics layer contains MCDA ranking, normalization, sensitivity analysis, and machine learning only where it adds value. FastAPI exposes regional processing and result-retrieval endpoints. The web layer provides the map-based review interface.

The innovation is the workflow, not a claim that every individual algorithm is new. Traditional scouting is site-by-site. Helios performs regional screening. Traditional checks separate technical and grid review. Helios combines them. Traditional uncertainty is often implicit. Helios exposes confidence and stability. Traditional validation depends heavily on analyst judgment. Helios records a measurable baseline.

This separation also makes the prototype extensible. A new irradiance model or economic dataset can replace one feature provider without rewriting the map or ranking interface.”

**Demonstrate:** Show the shared deployed application, then briefly show the API, feature, validation, and data directories in the repository.

## Speaker 6 - Feasibility, expected impact, validation, and future

**PDF alignment:** Slide 7 - Feasibility & Expected Impact  
**Prototype screen:** Validation and evidence section of Candidate Analysis

“The prototype is feasible because it uses established Python, GIS, web, and publicly available data components. Batch regional processing and PostGIS provide a path to larger study areas. Confidence flags and sensitivity analysis address missing or uncertain data.

We evaluated Helios against a frozen manual scouting baseline for the same Kharghar area. Manual scouting took 28 minutes. The Helios shortlist took approximately 4 minutes.

At K equal to 2, manual Precision@2 was 0.00 and Helios Precision@2 was 0.50. Manual nDCG@2 was 0.3066 and Helios nDCG@2 was 0.8066. These are hackathon measurements from a checked-in fixture, not a claim that every city will show the same result.

The expected impact is more candidates screened per analyst-hour and better focus for fieldwork. The final system should produce a ranked shortlist with suitability, confidence, stability, site-review priority, and an explanation of the contributing factors.

What remains is to connect the production irradiance and PV-yield models, improve shadow and roof-obstacle modelling, add validated CAPEX, payback, and LCOE inputs, scale to larger regions, and validate against more cities and real field outcomes.

Helios is a screening and inspection-prioritization system. It does not replace structural load testing, electrical design, utility interconnection approval, legal lease work, or final EPC decisions. Thank you.”

**Demonstrate:** Show the validation metrics and the limitation note. End on the full 2D-to-3D workflow and ranked candidate view.

## Final hand-off sentence

“Our core innovation is one explainable workflow from regional discovery to investment-prioritization support: discover candidates first, screen them consistently, rank them transparently, and send the strongest or most uncertain sites for field validation.”

