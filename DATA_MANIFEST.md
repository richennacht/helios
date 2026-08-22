# Helios Data Provenance Manifest (Kharghar AOI)

| Layer | Source | CRS | License | Notes / Assumptions |
| :--- | :--- | :--- | :--- | :--- |
| **Building Footprints** | OpenStreetMap (OSM) | EPSG:4326 | ODbL 1.0 | 5,029 validated polygons with metric area >= 20 m². |
| **Road Network** | OpenStreetMap (OSM) | EPSG:4326 | ODbL 1.0 | 2,975 road segment centerlines for distance-to-road checks. |
| **Power Grid** | OpenStreetMap (OSM) | EPSG:4326 | ODbL 1.0 | 72 substation, transformer, and power node elements. |
| **Terrain Elevation** | Copernicus DEM 30m / Survey Baseline | EPSG:4326 | Open Data | Base terrain heights ranging from 10m to 65m above sea level. |
| **Solar Irradiance** | MNRE India / NREL | Tabular | Public Domain | 1,980 kWh/m²/year GHI registered for Kharghar coordinates. |
| **Economic Tariffs** | MSEDCL Rate Order | Tabular | Regulatory Doc | Commercial (₹9.50/kWh) and Residential (₹7.20/kWh) baselines. |