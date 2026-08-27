# Solar and access factor decomposition

Helios no longer treats irradiance as one unexplained number. The solar-resource adapter can expose:

- **GHI:** global horizontal irradiance.
- **DNI:** direct normal irradiance.
- **DHI:** diffuse horizontal irradiance.
- **Seasonal variability:** how much the resource changes across months.
- **Temperature loss:** estimated PV efficiency loss under heat.
- **Weather confidence:** completeness and agreement of the source time series.

The initial implementation is in `helios/features/solar/resource_breakdown.py`. It accepts source IDs so NASA POWER, NIWE, PVGIS, Global Solar Atlas, ISRO/VEDAS, or ERA5 adapters can be compared without changing the ranking contract.

## Access and repairability

OSM/Geofabrik road and power layers can provide screening features for:

- road distance for equipment access;
- mapped grid distance;
- a documented repairability/access score;
- a logistics and access-cost adder.

The initial deterministic cost helper is `calculate_access_cost_feature` in `helios/features/economics/economics.py`. It is a screening estimate, not a contractor quote or utility-connection cost.

## Source roles

- [NASA POWER](https://power.larc.nasa.gov/): solar and meteorological time series.
- [NIWE](https://niwe.res.in/): Indian solar/wind measurement and resource context.
- [PVGIS](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis_en): PV production reference and cross-check.
- [Global Solar Atlas](https://globalsolaratlas.info/download/india): long-term regional solar-resource context.
- [ERA5](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels): historical reanalysis and uncertainty checks.
- [Geofabrik](https://download.geofabrik.de/): reproducible OSM extracts for roads and mapped power infrastructure.
- [OpenStreetMap](https://www.openstreetmap.org/copyright): feature-level road and power attribution.

Every adapter must record source, version/date, resolution, coverage, license, and missingness. Historical ERA5 analysis should be presented as a time-aware comparison, not silently mixed into a current-year value.
