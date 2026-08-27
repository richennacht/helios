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
Add another profile only after recording its official source document, source date,
currency, geographic coverage, capacity bands, confidence and caveats in
`government_economic_profiles.json`.

