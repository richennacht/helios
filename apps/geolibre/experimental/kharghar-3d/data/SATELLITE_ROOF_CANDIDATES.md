# Satellite roof-candidate intake

This is an opt-in path for buildings visible in satellite imagery but absent from the registered fused building layer.

## Intake file

Add a GeoJSON Polygon feature to `data/satellite_roof_candidates.geojson` with these properties:

```json
{
  "candidate_id": "satellite-kharghar-001",
  "source": "manual_satellite_digitization",
  "source_date": "YYYY-MM-DD",
  "imagery_source": "provider and acquisition date",
  "verification_status": "unverified",
  "display_height_m": 4,
  "roof_type": "unknown",
  "height_source": null,
  "roof_plane_source": null
}
```

The viewer renders this feature as a yellow, ground-up provisional extrusion. The fallback height is 4 m only for visual discoverability.

## Safety boundary

This is not a LoD2 building model. A verified LoD2 representation requires source-backed height plus roof-plane/ridge geometry. Satellite candidates are excluded from the height score, solar calculation, economics, and final ranking until those attributes are independently verified and transferred into the registered feature contracts.
