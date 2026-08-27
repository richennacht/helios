# P3 research-informed solar-output factors and filters

## Scope

This is a screening layer for Helios, not a calibrated power-plant simulator. It consumes only Person 1's registered/cached weather and irradiance inputs and Person 2's already-usable roof area plus shading proxy. It does not download data, infer roof geometry, or rank candidates.

## Factors implemented

| Factor | Treatment | Input owner / recommended dataset |
|---|---|---|
| Plane-of-array irradiance | Primary annual energy driver | P1; NASA POWER ALLSKY_SFC_SW_DWN or an approved equivalent, converted and cached as annual POA |
| Air temperature | Temperature power correction | P1; NASA POWER T2M or ERA5-Land |
| Wind speed | Cooling term in the NOCT-style screening temperature | P1; NASA POWER WS2M or ERA5-Land |
| Shading | Explicit P2 proxy loss, applied once | P2 spatial_features |
| Soiling | Explicit declared loss, never silently defaulted | Registered scenario or a local monitored source |
| Inverter, system and degradation losses | Explicit, separately recorded assumptions | P3 assumption set |
| Roof usable area | Capacity driver; no second packing reduction | P2 spatial_features |

The factor filter rejects non-positive irradiance, impossible temperature/wind values, out-of-range loss/confidence values, and missing source period, date, ID or checksum. It also rejects rent, capex or energy-value observations without currency, source ID and source date.

## Modeling boundary

The annual formula is:

    annual yield = capacity * POA * shading * (1 - soiling)
                   * PR_excluding_inverter * inverter * temperature * degradation

Performance ratio deliberately excludes shading, soiling, inverter and degradation. Usable_area_m2 is already usable (P2), so it is not reduced again. Reference_year=1 makes degradation zero unless a later reference year is explicitly requested.

The simple economics score uses gross payback only for within-run normalization. It excludes O&M, finance, tax, replacement, tariff escalation, degradation beyond the chosen reference period, and rent. It is not a bankable measure.

## Sources

- King et al., Photovoltaic Array Performance Model, Sandia SAND2004-3535, DOI: 10.2172/919131.
- Soto et al., Improvement and validation of a model for photovoltaic array performance, DOI: 10.1016/j.solener.2005.06.010.
- Skoplaki and Palyvos, temperature/power correlation review, DOI: 10.1016/j.solener.2008.10.008.
- Sandia PV Performance Modeling Collaborative, [single-diode model guide](https://pvpmc.sandia.gov/modeling-guide/2-dc-module-iv/single-diode-equivalent-circuit-models/).
- Holmgren et al., pvlib-python, DOI: 10.21105/joss.00884.

The supplied DOI text contained concatenated links, so only identifiable PV-performance references above were used as model evidence. Ambiguous DOI fragments are not treated as validated sources.

## Reproduction

Run:

    python -m pytest tests/features/solar/test_factor_filter.py
    ruff check helios/features/solar helios/features/economics tests/features/solar

The fixture p3_factor_filtered_handoff.json contains a P4-compatible p3_table and a separate provenance sidecar.
