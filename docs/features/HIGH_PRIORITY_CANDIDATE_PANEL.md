# High-priority candidate panel

`high-priority-scorecard.html` is a standalone, static extension for the GeoLibre prototype. It presents the existing Person 2, Person 3, and Person 4 demo fixture in one explainable candidate view.

## Implemented from the shared fixture

- Solar suitability using the Person 3 generation score and annual energy yield.
- Roof area and shading factor from Person 2.
- Grid proximity using nearest-grid distance and the Person 2 grid score.
- CAPEX, annual energy value scenario, gross payback, economic score, and confidence.
- An overall suitability calculation using the frozen Person 4 weights: generation 35%, physical 30%, grid 20%, economics 15%.

## Deliberately marked unavailable

- Orientation, roof slope, and road/infrastructure access: no source-backed values occur in the frozen fixture.
- LCOE: requires explicit asset lifetime, O&M, financing, tariff, and rent treatment.
- Rent provenance: the fixture provides a monthly amount for some candidates but no source, currency, or source date.

The panel labels all source-derived and calculated values as prototype/fixture-backed. It must not be presented as measured irradiance, tariff, grid, or commercial data.

## Review path

Open the page beside the existing GeoLibre prototype and use the candidate selector. The formula view makes the scoring contribution of every frozen criterion visible. When validated source layers are supplied, the page can be embedded into the map viewer and the unavailable fields can be replaced without changing the scoring explanation.
