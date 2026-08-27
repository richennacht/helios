# Government economic inputs

The Kharghar viewer resolves the selected AOI against a checked-in government economic
profile and automatically fills the CAPEX and avoided-energy inputs. The browser does not
scrape government PDFs at runtime. This keeps the demo deterministic and makes the source,
date, currency, capacity band and confidence visible and reviewable.

The first profile covers Maharashtra:

- CAPEX uses MNRE's FY 2019-20 grid-connected rooftop benchmark. It is the latest rooftop
  benchmark currently listed on MNRE's benchmark-cost page, but it is historical and must
  not be presented as a current vendor quote.
- Energy value uses the CEA publication dated 31 March 2025, compiled from MERC tariff
  orders, for LT-II non-residential/commercial consumers effective 1 April 2024.
- The candidate PV capacity selects the published capacity/load band. For electricity
  tariffs this is only a screening proxy; the actual sanctioned load and consumer category
  must be confirmed with the DISCOM.

Unsupported AOIs remain unavailable rather than silently receiving Maharashtra values.
Candidates outside a source's published capacity bands are excluded and counted rather
than extrapolated or allowed to stop the other candidates from calculating.

The economic analysis runs a discounted annual cash-flow simulation for every supported
building. Total CAPEX, annual generation, annual value and absolute O&M differ by building.
The O&M rate, degradation rate, project life and WACC are shared portfolio assumptions.
The tariff rate is shared only where the registered consumer category and capacity/load
band match; otherwise the applicable government band is selected per building. Results
are ranked by profitability index, with NPV as the tie-breaker, so large roofs do not rank
first merely because their total project value is larger.

Each ranked result is also a map action. Selecting it switches to the existing 3D viewer,
highlights the corresponding footprint, flies the camera to the building and opens its
height/provenance popup.

Add another profile only after recording its official source document, source date,
currency, geographic coverage, capacity bands, confidence and caveats in
`government_economic_profiles.json`.
