"""Stable reason-code catalog for API and GeoLibre consumers."""

from helios.ranking.contracts import ExclusionReason

EXCLUSION_REASON_DESCRIPTIONS = {
    ExclusionReason.USABLE_AREA_BELOW_MINIMUM: "Usable roof area is below the scenario minimum.",
    ExclusionReason.INVALID_EXCHANGE_GEOMETRY: (
        "Candidate geometry is not a valid Point, Polygon or MultiPolygon exchange geometry."
    ),
    ExclusionReason.SHADING_FACTOR_BELOW_MINIMUM: (
        "Retained-light shading factor is below the scenario minimum."
    ),
    ExclusionReason.GRID_DISTANCE_ABOVE_SCREENING_LIMIT: (
        "Mapped grid-proximity distance exceeds the screening limit."
    ),
    ExclusionReason.ESTIMATED_COST_ABOVE_BUDGET: (
        "Estimated screening cost exceeds the scenario budget."
    ),
    ExclusionReason.ESTIMATED_COST_MISSING_FOR_BUDGET_FILTER: (
        "A budget is active but the candidate has no comparable estimated cost."
    ),
}


def exclusion_reason_catalog() -> dict[str, str]:
    """Return JSON-ready reason codes and stable human descriptions."""

    return {
        reason.value: description
        for reason, description in EXCLUSION_REASON_DESCRIPTIONS.items()
    }
