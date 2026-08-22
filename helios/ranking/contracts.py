"""Versioned Person 4 ranking contracts.

These models deliberately keep Person 2, Person 3, Person 5 and Person 6
handoffs separate. The ranking engine joins them by ``candidate_id`` and fails
closed when versions or candidate sets disagree.
"""

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RankingMode(StrEnum):
    NOMINAL = "nominal_mcda"
    ROBUST_ACCEPTABILITY = "robust_acceptability"


class WeightPreset(StrEnum):
    BALANCED = "balanced"
    ENERGY_FIRST = "energy_first"
    COST_FIRST = "cost_first"


class ValidationDecision(StrEnum):
    INSPECT = "inspect"
    UNCERTAIN = "uncertain"
    REJECT = "reject"


class DecisionStatus(StrEnum):
    STABLE = "stable"
    REVIEW_REQUIRED = "review_required"
    UNSTABLE = "unstable"
    EXCLUDED = "excluded"


class ExclusionReason(StrEnum):
    USABLE_AREA_BELOW_MINIMUM = "usable_area_below_minimum"
    INVALID_EXCHANGE_GEOMETRY = "invalid_exchange_geometry"
    SHADING_FACTOR_BELOW_MINIMUM = "shading_factor_below_minimum"
    GRID_DISTANCE_ABOVE_SCREENING_LIMIT = "grid_distance_above_screening_limit"
    ESTIMATED_COST_ABOVE_BUDGET = "estimated_cost_above_budget"
    ESTIMATED_COST_MISSING_FOR_BUDGET_FILTER = "estimated_cost_missing_for_budget_filter"


class P2CandidateRow(BaseModel):
    """Normalized spatial/physical features owned by Person 2."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1)
    geometry: dict[str, Any]
    usable_area_m2: float = Field(ge=0)
    shading_factor: float = Field(ge=0, le=1)
    grid_distance_m: float = Field(ge=0)
    physical_score: float = Field(ge=0, le=1)
    grid_score: float = Field(ge=0, le=1)
    feature_version: str = Field(min_length=1)


class P3CandidateRow(BaseModel):
    """Normalized generation/economic features owned by Person 3."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1)
    annual_yield_kwh: float = Field(ge=0)
    estimated_cost_inr: float | None = Field(default=None, ge=0)
    estimated_rent_inr_month: float | None = Field(default=None, ge=0)
    generation_score: float = Field(ge=0, le=1)
    economics_score: float = Field(ge=0, le=1)
    assumption_version: str = Field(min_length=1)


class CriterionConfidence(BaseModel):
    """Evidence confidence, used to size uncertainty - never as a reward."""

    model_config = ConfigDict(extra="forbid")

    generation: float = Field(ge=0, le=1)
    physical: float = Field(ge=0, le=1)
    grid: float = Field(ge=0, le=1)
    economics: float = Field(ge=0, le=1)


class ConfidenceRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1)
    overall_confidence: float = Field(ge=0, le=1)
    criteria: CriterionConfidence
    confidence_version: str = Field(min_length=1)


class WeightProfile(BaseModel):
    """Stakeholder preferences for benefits; confidence is not a benefit."""

    model_config = ConfigDict(extra="forbid")

    generation: float = Field(default=0.35, ge=0)
    physical: float = Field(default=0.30, ge=0)
    grid: float = Field(default=0.20, ge=0)
    economics: float = Field(default=0.15, ge=0)

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> "WeightProfile":
        if abs(sum(self.model_dump().values()) - 1.0) > 1e-6:
            raise ValueError("Person 4 ranking weights must sum to 1.0")
        return self


class RankingScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = "balanced"
    minimum_usable_area_m2: float = Field(default=40, ge=0)
    maximum_grid_distance_m: float | None = Field(default=2000, gt=0)
    minimum_shading_factor: float | None = Field(default=None, ge=0, le=1)
    budget_inr: float | None = Field(default=None, gt=0)
    require_cost_when_budgeted: bool = True
    top_k: int = Field(default=3, ge=1)


class RobustnessConfig(BaseModel):
    """Versioned assumptions for confidence-calibrated rank acceptability."""

    model_config = ConfigDict(extra="forbid")

    method_version: Literal["ccra-v1"] = "ccra-v1"
    iterations: int = Field(default=2000, ge=100, le=100_000)
    random_seed: int = 41
    feature_perturbation_at_zero_confidence: float = Field(default=0.20, ge=0, le=0.5)
    weight_relative_tolerance: float = Field(default=0.10, ge=0, le=0.5)
    stable_top_k_probability: float = Field(default=0.80, ge=0, le=1)
    review_top_k_probability: float = Field(default=0.40, ge=0, le=1)
    maximum_stable_rank_span: int = Field(default=2, ge=0)

    @model_validator(mode="after")
    def review_threshold_not_above_stable(self) -> "RobustnessConfig":
        if self.review_top_k_probability > self.stable_top_k_probability:
            raise ValueError("review threshold cannot exceed stable threshold")
        return self


class ValidationLabel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1)
    decision: ValidationDecision
    reviewer_id: str = Field(min_length=1)
    reason_codes: list[str] = Field(default_factory=list)
    blinded: bool


class ValidationSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label_set_version: str = Field(min_length=1)
    labels: list[ValidationLabel]
    evaluation_k: int = Field(default=3, ge=1)
    manual_candidate_order: list[str] = Field(default_factory=list)
    manual_shortlist_minutes: float | None = Field(default=None, gt=0)
    helios_shortlist_minutes: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def labels_are_unique(self) -> "ValidationSet":
        ids = [label.candidate_id for label in self.labels]
        if len(ids) != len(set(ids)):
            raise ValueError("validation labels must contain one row per candidate")
        if len(self.manual_candidate_order) != len(set(self.manual_candidate_order)):
            raise ValueError("manual candidate order contains duplicate IDs")
        return self


class P5RankingRequest(BaseModel):
    """Complete inbound contract that Person 5 can call without domain logic."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["person4.v1"] = "person4.v1"
    feature_dictionary_version: Literal["person4.features-v1"]
    request_id: str = Field(min_length=1)
    assumption_version: str = Field(min_length=1)
    scenario: RankingScenario = Field(default_factory=RankingScenario)
    weights: WeightProfile = Field(default_factory=WeightProfile)
    ranking_mode: RankingMode = RankingMode.ROBUST_ACCEPTABILITY
    robustness: RobustnessConfig = Field(default_factory=RobustnessConfig)
    p2_table: list[P2CandidateRow] = Field(min_length=1)
    p3_table: list[P3CandidateRow] = Field(min_length=1)
    confidence_table: list[ConfidenceRow] = Field(min_length=1)
    validation: ValidationSet | None = None

    @model_validator(mode="after")
    def handoffs_align(self) -> "P5RankingRequest":
        p2_ids = [row.candidate_id for row in self.p2_table]
        p3_ids = [row.candidate_id for row in self.p3_table]
        confidence_ids = [row.candidate_id for row in self.confidence_table]
        for name, ids in (("P2", p2_ids), ("P3", p3_ids), ("confidence", confidence_ids)):
            if len(ids) != len(set(ids)):
                raise ValueError(f"{name} table contains duplicate candidate IDs")
        if set(p2_ids) != set(p3_ids) or set(p2_ids) != set(confidence_ids):
            raise ValueError("P2, P3 and confidence tables must contain identical candidate IDs")
        wrong_versions = {
            row.assumption_version
            for row in self.p3_table
            if row.assumption_version != self.assumption_version
        }
        if wrong_versions:
            raise ValueError("P3 assumption_version does not match request assumption_version")
        p2_versions = {row.feature_version for row in self.p2_table}
        if len(p2_versions) != 1:
            raise ValueError("P2 table must contain one feature_version per request")
        confidence_versions = {row.confidence_version for row in self.confidence_table}
        if len(confidence_versions) != 1:
            raise ValueError("confidence table must contain one confidence_version per request")
        if self.scenario.top_k > len(p2_ids):
            raise ValueError("top_k cannot exceed the candidate count")
        if self.validation:
            unknown_labels = {
                label.candidate_id for label in self.validation.labels
            } - set(p2_ids)
            unknown_manual = set(self.validation.manual_candidate_order) - set(p2_ids)
            if unknown_labels or unknown_manual:
                raise ValueError("validation data references unknown candidate IDs")
        return self


class CandidateStability(BaseModel):
    candidate_id: str
    probability_rank_1: float = Field(ge=0, le=1)
    probability_top_k: float = Field(ge=0, le=1)
    expected_rank: float = Field(ge=1)
    rank_p05: int = Field(ge=1)
    rank_p50: int = Field(ge=1)
    rank_p95: int = Field(ge=1)
    expected_score: float = Field(ge=0, le=1)
    score_std: float = Field(ge=0)
    rank_acceptability: dict[int, float]
    decision_status: DecisionStatus


class RankedCandidate(BaseModel):
    candidate_id: str
    geometry: dict[str, Any]
    eligible: bool
    exclusion_reasons: list[ExclusionReason]
    rank: int | None
    nominal_rank: int | None
    robust_rank: int | None
    nominal_score: float | None
    component_contributions: dict[str, float]
    overall_confidence: float
    pareto_optimal: bool | None
    decision_status: DecisionStatus


class CandidateExplanation(BaseModel):
    candidate_id: str
    positive_reasons: list[str]
    caution_reasons: list[str]
    trace: dict[str, float | str]


class StabilityReport(BaseModel):
    method_version: str
    iterations: int
    random_seed: int
    top_k: int
    mean_nominal_top_k_retention: float = Field(ge=0, le=1)
    candidates: list[CandidateStability]
    assumptions: list[str]


class MetricSet(BaseModel):
    method: str
    evaluated_k: int
    labelled_candidates: int
    precision_at_k: float | None = Field(default=None, ge=0, le=1)
    recall_at_k: float | None = Field(default=None, ge=0, le=1)
    ndcg_at_k: float | None = Field(default=None, ge=0, le=1)
    shortlist_minutes: float | None = Field(default=None, gt=0)


class EvaluationReport(BaseModel):
    status: Literal["not_provided", "insufficient_labels", "completed"]
    label_set_version: str | None = None
    helios: MetricSet | None = None
    manual_baseline: MetricSet | None = None
    baselines: list[MetricSet] = Field(default_factory=list)
    deltas: dict[str, float] = Field(default_factory=dict)
    deltas_by_baseline: dict[str, dict[str, float]] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class RankingBundle(BaseModel):
    contract_version: Literal["person4.v1"] = "person4.v1"
    request_id: str
    assumption_version: str
    input_versions: dict[str, str]
    ranking_mode: RankingMode
    ranked_candidates: list[RankedCandidate]
    explanations: list[CandidateExplanation]
    stability_report: StabilityReport
    evaluation_report: EvaluationReport

    @model_validator(mode="after")
    def output_is_internally_consistent(self) -> "RankingBundle":
        candidate_ids = [row.candidate_id for row in self.ranked_candidates]
        explanation_ids = [row.candidate_id for row in self.explanations]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("ranked output contains duplicate candidate IDs")
        if len(explanation_ids) != len(set(explanation_ids)):
            raise ValueError("explanation output contains duplicate candidate IDs")
        if set(candidate_ids) != set(explanation_ids):
            raise ValueError("ranked candidates and explanations must contain identical IDs")

        eligible = [row for row in self.ranked_candidates if row.eligible]
        ranks = sorted(row.rank for row in eligible if row.rank is not None)
        if ranks != list(range(1, len(eligible) + 1)):
            raise ValueError("eligible candidate ranks must be unique and contiguous")
        for row in eligible:
            if (
                row.nominal_score is None
                or row.nominal_rank is None
                or row.robust_rank is None
                or row.pareto_optimal is None
                or row.decision_status is DecisionStatus.EXCLUDED
            ):
                raise ValueError("eligible candidate output is incomplete")
            if abs(sum(row.component_contributions.values()) - row.nominal_score) > 1e-5:
                raise ValueError("component contributions must sum to nominal score")
        for row in self.ranked_candidates:
            if row.eligible:
                continue
            if any(
                value is not None
                for value in (
                    row.rank,
                    row.nominal_rank,
                    row.robust_rank,
                    row.nominal_score,
                    row.pareto_optimal,
                )
            ) or row.component_contributions:
                raise ValueError("excluded candidate must not contain ranking values")
            if row.decision_status is not DecisionStatus.EXCLUDED:
                raise ValueError("excluded candidate must use excluded decision status")

        stability_ids = {row.candidate_id for row in self.stability_report.candidates}
        if stability_ids != {row.candidate_id for row in eligible}:
            raise ValueError("stability report must contain every eligible candidate exactly once")
        return self
