# Solar and techno-economic features

Person 3 converts Person 2 spatial features and Person 1 registered resource/economic inputs into an auditable, screening-only handoff. No function in `helios/features/solar` or `helios/features/economics` fetches data, recalculates geometry, ranks candidates, or writes to the database.

## Inputs

- `candidate_id` - stable join key.
- `usable_area_m2`, `shading_factor`, `spatial_confidence` - supplied by Person 2.
- `annual_poa_kwh_m2`, resource period, source ID, checksum and solar confidence - a registered/cached solar source prepared by Person 1.
- Dated capex and energy-value inputs, with currency and source ID - registered by Person 1.

## Formula

```text
installable_capacity_kwp = usable_area_m2 * usable_area_factor / area_per_kwp_m2

annual_yield_kwh = installable_capacity_kwp * annual_poa_kwh_m2
                   * shading_factor * performance_ratio * inverter_efficiency
```

Shading, performance and inverter losses are each exposed separately. The performance ratio is an explicitly declared aggregate of non-shading system losses; shading is never applied again inside it.

## Economics

Indicative cost, energy value and simple payback are calculated only when their dated registered inputs exist. Rent remains `None` when unavailable. Outputs are screening estimates, not financial, tariff, lease, structural or interconnection approvals.

## Reproduce

```bash
python -m pytest tests/features/solar/test_yield_model.py
ruff check helios/features/solar helios/features/economics tests/features/solar
```

The tests include a manual 100 m2 Kharghar-style scenario, a shading monotonicity check and missing-commercial-data checks.
