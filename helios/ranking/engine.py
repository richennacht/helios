"""Person 4 deterministic and confidence-calibrated ranking engine."""

from __future__ import annotations

from dataclasses import dataclass
from math import log2, sqrt
from random import Random
from statistics import mean

from helios.ranking.contracts import (
    CandidateExplanation,
    CandidateStability,
    DecisionStatus,
    EvaluationReport,
    ExclusionReason,
    MetricSet,
    P2CandidateRow,
    P3CandidateRow,
    P5RankingRequest,
    RankedCandidate,
    RankingBundle,
    RankingMode,
    StabilityReport,
    ValidationDecision,
    ValidationSet,
)
from helios.ranking.features import CRITERIA, FEATURE_DICTIONARY_VERSION

POSITIVE_LABELS = {
    "generation": "strong modeled annual-generation potential",
    "physical": "strong usable-roof and coarse-shading profile",
    "grid": "favorable grid-proximity screening score",
    "economics": "favorable early techno-economic screening score",
}


@dataclass(frozen=True)
class _Candidate:
    p2: P2CandidateRow
    p3: P3CandidateRow
    confidence: dict[str, float]
    overall_confidence: float

    @property
    def candidate_id(self) -> str:
        return self.p2.candidate_id

    @property
    def values(self) -> dict[str, float]:
        return {
            "generation": self.p3.generation_score,
            "physical": self.p2.physical_score,
            "grid": self.p2.grid_score,
            "economics": self.p3.economics_score,
        }


def rank_candidates(request: P5RankingRequest) -> RankingBundle:
    """Run screening, MCDA, robustness, explanations and optional evaluation."""
    if request.ranking_mode is RankingMode.FUZZY_ML_CHALLENGER:
        from helios.ranking.ml_fuzzy_scheduler import rank_candidates_fuzzy_ml

        return rank_candidates_fuzzy_ml(request)

    joined = _join_inputs(request)
    exclusions = {
        candidate.candidate_id: _exclusion_reasons(candidate, request)
        for candidate in joined
    }
    eligible = [candidate for candidate in joined if not exclusions[candidate.candidate_id]]
    nominal_scores = {
        candidate.candidate_id: _weighted_score(candidate.values, request.weights.model_dump())
        for candidate in eligible
    }
    nominal_order = sorted(
        eligible, key=lambda c: (-nominal_scores[c.candidate_id], c.candidate_id)
    )
    nominal_ranks = {
        candidate.candidate_id: index
        for index, candidate in enumerate(nominal_order, 1)
    }
    pareto_ids = _pareto_optimal_ids(eligible)

    stability, robust_ranks = _stability_report(eligible, nominal_ranks, request)
    stability_by_id = {row.candidate_id: row for row in stability.candidates}

    if request.ranking_mode is RankingMode.ROBUST_ACCEPTABILITY:
        selected_ranks = robust_ranks
    else:
        selected_ranks = nominal_ranks

    ranked_candidates: list[RankedCandidate] = []
    explanations: list[CandidateExplanation] = []
    for candidate in joined:
        candidate_id = candidate.candidate_id
        is_eligible = not exclusions[candidate_id]
        contributions = (
            _component_contributions(candidate.values, request.weights.model_dump())
            if is_eligible
            else {}
        )
        status = (
            stability_by_id[candidate_id].decision_status
            if is_eligible
            else DecisionStatus.EXCLUDED
        )
        ranked_candidates.append(
            RankedCandidate(
                candidate_id=candidate_id,
                geometry=candidate.p2.geometry,
                eligible=is_eligible,
                exclusion_reasons=exclusions[candidate_id],
                rank=selected_ranks.get(candidate_id),
                nominal_rank=nominal_ranks.get(candidate_id),
                robust_rank=robust_ranks.get(candidate_id),
                nominal_score=nominal_scores.get(candidate_id),
                component_contributions=contributions,
                overall_confidence=candidate.overall_confidence,
                pareto_optimal=candidate_id in pareto_ids if is_eligible else None,
                decision_status=status,
            )
        )
        explanations.append(
            _explain(
                candidate,
                contributions,
                exclusions[candidate_id],
                stability_by_id.get(candidate_id),
                candidate_id in pareto_ids if is_eligible else None,
            )
        )

    ranked_candidates.sort(
        key=lambda row: (
            not row.eligible,
            row.rank if row.rank is not None else 10**9,
            row.candidate_id,
        )
    )
    explanation_order = {row.candidate_id: index for index, row in enumerate(ranked_candidates)}
    explanations.sort(key=lambda row: explanation_order[row.candidate_id])
    baseline_orders = {
        "solar_only": [
            candidate.candidate_id
            for candidate in sorted(
                eligible,
                key=lambda row: (-row.values["generation"], row.candidate_id),
            )
        ],
        "equal_weight_mcda": [
            candidate.candidate_id
            for candidate in sorted(
                eligible,
                key=lambda row: (
                    -mean(row.values.values()),
                    row.candidate_id,
                ),
            )
        ],
        "balanced_nominal_mcda": [candidate.candidate_id for candidate in nominal_order],
    }
    evaluation = _evaluate(ranked_candidates, request.validation, baseline_orders)

    return RankingBundle(
        request_id=request.request_id,
        assumption_version=request.assumption_version,
        input_versions={
            "feature_dictionary": FEATURE_DICTIONARY_VERSION,
            "p2_features": request.p2_table[0].feature_version,
            "p3_assumptions": request.assumption_version,
            "confidence": request.confidence_table[0].confidence_version,
        },
        ranking_mode=request.ranking_mode,
        ranked_candidates=ranked_candidates,
        explanations=explanations,
        stability_report=stability,
        evaluation_report=evaluation,
    )


def _join_inputs(request: P5RankingRequest) -> list[_Candidate]:
    p3_by_id = {row.candidate_id: row for row in request.p3_table}
    confidence_by_id = {row.candidate_id: row for row in request.confidence_table}
    joined: list[_Candidate] = []
    for p2 in request.p2_table:
        confidence_row = confidence_by_id[p2.candidate_id]
        criteria = confidence_row.criteria.model_dump()
        effective = {
            name: min(value, confidence_row.overall_confidence)
            for name, value in criteria.items()
        }
        joined.append(
            _Candidate(
                p2=p2,
                p3=p3_by_id[p2.candidate_id],
                confidence=effective,
                overall_confidence=confidence_row.overall_confidence,
            )
        )
    return joined


def _exclusion_reasons(
    candidate: _Candidate, request: P5RankingRequest
) -> list[ExclusionReason]:
    reasons: list[ExclusionReason] = []
    scenario = request.scenario
    if candidate.p2.usable_area_m2 < scenario.minimum_usable_area_m2:
        reasons.append(ExclusionReason.USABLE_AREA_BELOW_MINIMUM)
    if not _geometry_is_valid(candidate.p2.geometry):
        reasons.append(ExclusionReason.INVALID_EXCHANGE_GEOMETRY)
    if (
        scenario.minimum_shading_factor is not None
        and candidate.p2.shading_factor < scenario.minimum_shading_factor
    ):
        reasons.append(ExclusionReason.SHADING_FACTOR_BELOW_MINIMUM)
    if (
        scenario.maximum_grid_distance_m is not None
        and candidate.p2.grid_distance_m > scenario.maximum_grid_distance_m
    ):
        reasons.append(ExclusionReason.GRID_DISTANCE_ABOVE_SCREENING_LIMIT)
    if (
        scenario.budget_inr is not None
        and candidate.p3.estimated_cost_inr is not None
        and candidate.p3.estimated_cost_inr > scenario.budget_inr
    ):
        reasons.append(ExclusionReason.ESTIMATED_COST_ABOVE_BUDGET)
    if (
        scenario.budget_inr is not None
        and scenario.require_cost_when_budgeted
        and candidate.p3.estimated_cost_inr is None
    ):
        reasons.append(ExclusionReason.ESTIMATED_COST_MISSING_FOR_BUDGET_FILTER)
    return reasons


def _geometry_is_valid(geometry: dict) -> bool:
    """Perform a dependency-free sanity check on exchange GeoJSON geometry."""

    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "Point":
        return _valid_position(coordinates)
    if geometry_type == "Polygon":
        return _valid_polygon(coordinates)
    if geometry_type == "MultiPolygon":
        return (
            isinstance(coordinates, list)
            and bool(coordinates)
            and all(_valid_polygon(polygon) for polygon in coordinates)
        )
    return False


def _valid_position(position: object) -> bool:
    if not isinstance(position, list) or len(position) < 2:
        return False
    longitude, latitude = position[:2]
    return (
        isinstance(longitude, int | float)
        and not isinstance(longitude, bool)
        and isinstance(latitude, int | float)
        and not isinstance(latitude, bool)
        and -180 <= longitude <= 180
        and -90 <= latitude <= 90
    )


def _valid_polygon(coordinates: object) -> bool:
    if not isinstance(coordinates, list) or not coordinates:
        return False
    for ring in coordinates:
        if not isinstance(ring, list) or len(ring) < 4:
            return False
        if not all(_valid_position(position) for position in ring):
            return False
        if ring[0][:2] != ring[-1][:2]:
            return False
    return True


def _pareto_optimal_ids(candidates: list[_Candidate]) -> set[str]:
    """Return non-dominated candidates over the four normalized benefit criteria."""

    optimal: set[str] = set()
    for candidate in candidates:
        dominated = any(
            other.candidate_id != candidate.candidate_id
            and all(other.values[name] >= candidate.values[name] for name in CRITERIA)
            and any(other.values[name] > candidate.values[name] for name in CRITERIA)
            for other in candidates
        )
        if not dominated:
            optimal.add(candidate.candidate_id)
    return optimal


def _component_contributions(
    values: dict[str, float], weights: dict[str, float]
) -> dict[str, float]:
    return {criterion: round(values[criterion] * weights[criterion], 6) for criterion in CRITERIA}


def _weighted_score(values: dict[str, float], weights: dict[str, float]) -> float:
    return round(sum(values[name] * weights[name] for name in CRITERIA), 6)


def _stability_report(
    candidates: list[_Candidate], nominal_ranks: dict[str, int], request: P5RankingRequest
) -> tuple[StabilityReport, dict[str, int]]:
    config = request.robustness
    if not candidates:
        return (
            StabilityReport(
                method_version=config.method_version,
                iterations=config.iterations,
                random_seed=config.random_seed,
                top_k=request.scenario.top_k,
                mean_nominal_top_k_retention=0,
                candidates=[],
                assumptions=_stability_assumptions(request),
            ),
            {},
        )

    random = Random(config.random_seed)
    top_k = min(request.scenario.top_k, len(candidates))
    nominal_top = {candidate_id for candidate_id, rank in nominal_ranks.items() if rank <= top_k}
    rank_samples = {candidate.candidate_id: [] for candidate in candidates}
    score_samples = {candidate.candidate_id: [] for candidate in candidates}
    retention_samples: list[float] = []
    base_weights = request.weights.model_dump()

    for _ in range(config.iterations):
        sampled_weights = _sample_weights(base_weights, config.weight_relative_tolerance, random)
        sampled_scores: dict[str, float] = {}
        for candidate in candidates:
            sampled_values = {
                criterion: _sample_value(
                    candidate.values[criterion],
                    candidate.confidence[criterion],
                    config.feature_perturbation_at_zero_confidence,
                    random,
                )
                for criterion in CRITERIA
            }
            sampled_scores[candidate.candidate_id] = _weighted_score(
                sampled_values, sampled_weights
            )
        sampled_order = sorted(sampled_scores, key=lambda cid: (-sampled_scores[cid], cid))
        sampled_top = set(sampled_order[:top_k])
        retention_samples.append(len(nominal_top & sampled_top) / top_k)
        for rank, candidate_id in enumerate(sampled_order, 1):
            rank_samples[candidate_id].append(rank)
            score_samples[candidate_id].append(sampled_scores[candidate_id])

    candidate_stability: list[CandidateStability] = []
    for candidate in candidates:
        candidate_id = candidate.candidate_id
        ranks = rank_samples[candidate_id]
        scores = score_samples[candidate_id]
        acceptability = {
            rank: round(ranks.count(rank) / config.iterations, 6)
            for rank in sorted(set(ranks))
        }
        p_top_k = sum(rank <= top_k for rank in ranks) / config.iterations
        p05 = _quantile_int(ranks, 0.05)
        p50 = _quantile_int(ranks, 0.50)
        p95 = _quantile_int(ranks, 0.95)
        rank_span = p95 - p05
        if (
            p_top_k >= config.stable_top_k_probability
            and rank_span <= config.maximum_stable_rank_span
        ):
            status = DecisionStatus.STABLE
        elif p_top_k >= config.review_top_k_probability:
            status = DecisionStatus.REVIEW_REQUIRED
        else:
            status = DecisionStatus.UNSTABLE
        score_mean = mean(scores)
        score_std = sqrt(mean([(score - score_mean) ** 2 for score in scores]))
        candidate_stability.append(
            CandidateStability(
                candidate_id=candidate_id,
                probability_rank_1=round(ranks.count(1) / config.iterations, 6),
                probability_top_k=round(p_top_k, 6),
                expected_rank=round(mean(ranks), 6),
                rank_p05=p05,
                rank_p50=p50,
                rank_p95=p95,
                expected_score=round(score_mean, 6),
                score_std=round(score_std, 6),
                rank_acceptability=acceptability,
                decision_status=status,
            )
        )

    candidate_stability.sort(
        key=lambda row: (
            -row.probability_top_k,
            row.expected_rank,
            -row.expected_score,
            row.candidate_id,
        )
    )
    robust_ranks = {
        candidate.candidate_id: rank for rank, candidate in enumerate(candidate_stability, 1)
    }
    return (
        StabilityReport(
            method_version=config.method_version,
            iterations=config.iterations,
            random_seed=config.random_seed,
            top_k=top_k,
            mean_nominal_top_k_retention=round(mean(retention_samples), 6),
            candidates=candidate_stability,
            assumptions=_stability_assumptions(request),
        ),
        robust_ranks,
    )


def _sample_weights(
    base: dict[str, float], tolerance: float, random: Random
) -> dict[str, float]:
    perturbed = {
        name: weight * random.uniform(1 - tolerance, 1 + tolerance)
        for name, weight in base.items()
    }
    total = sum(perturbed.values())
    return {name: value / total for name, value in perturbed.items()}


def _sample_value(value: float, confidence: float, maximum_width: float, random: Random) -> float:
    width = maximum_width * (1 - confidence)
    low = max(0.0, value - width)
    high = min(1.0, value + width)
    if low == high:
        return value
    return random.triangular(low, high, value)


def _quantile_int(values: list[int], probability: float) -> int:
    ordered = sorted(values)
    index = round((len(ordered) - 1) * probability)
    return ordered[index]


def _stability_assumptions(request: P5RankingRequest) -> list[str]:
    config = request.robustness
    return [
        "Criterion confidence controls uncertainty width and is not added as a benefit score.",
        (
            "At zero confidence, each normalized feature is sampled within +/-"
            f"{config.feature_perturbation_at_zero_confidence:.2f}; width shrinks linearly to zero."
        ),
        (
            "Weights are independently perturbed by up to +/-"
            f"{config.weight_relative_tolerance:.2f} and renormalized to sum to one."
        ),
        "Feature draws use bounded triangular distributions centered on the supplied value.",
        "These are scenario assumptions, not empirically calibrated error distributions yet.",
    ]


def _explain(
    candidate: _Candidate,
    contributions: dict[str, float],
    exclusions: list[ExclusionReason],
    stability: CandidateStability | None,
    pareto_optimal: bool | None,
) -> CandidateExplanation:
    if exclusions:
        return CandidateExplanation(
            candidate_id=candidate.candidate_id,
            positive_reasons=[],
            caution_reasons=[f"excluded: {reason.value}" for reason in exclusions],
            trace={"status": DecisionStatus.EXCLUDED.value},
        )
    strongest = sorted(contributions, key=lambda key: (-contributions[key], key))[:2]
    positives = [POSITIVE_LABELS[name] for name in strongest]
    cautions: list[str] = []
    if candidate.p2.shading_factor < 0.75:
        cautions.append("coarse shading proxy indicates possible obstruction losses")
    if candidate.p3.estimated_rent_inr_month is None:
        cautions.append(
            "rent is unavailable and the economic score uses documented fallback assumptions"
        )
    if candidate.overall_confidence < 0.65:
        cautions.append("input confidence is low; inspect provenance before field prioritization")
    if stability and stability.decision_status is not DecisionStatus.STABLE:
        cautions.append(
            "rank is sensitive to declared feature/weight uncertainty; human review is required"
        )
    trace: dict[str, float | str] = {
        f"contribution_{name}": value for name, value in contributions.items()
    }
    if stability:
        trace.update(
            {
                "probability_top_k": stability.probability_top_k,
                "rank_interval": f"{stability.rank_p05}-{stability.rank_p95}",
                "decision_status": stability.decision_status.value,
            }
        )
    if pareto_optimal is not None:
        trace["pareto_optimal"] = str(pareto_optimal).lower()
    return CandidateExplanation(
        candidate_id=candidate.candidate_id,
        positive_reasons=positives,
        caution_reasons=cautions,
        trace=trace,
    )


def _evaluate(
    ranked_candidates: list[RankedCandidate],
    validation: ValidationSet | None,
    baseline_orders: dict[str, list[str]],
) -> EvaluationReport:
    if validation is None:
        return EvaluationReport(
            status="not_provided",
            warnings=[
                "No locked validation labels were provided; no improvement claim is allowed."
            ],
        )
    label_by_id = {label.candidate_id: label.decision for label in validation.labels}
    eligible_order = [
        row.candidate_id
        for row in ranked_candidates
        if row.eligible and row.candidate_id in label_by_id
    ]
    if not eligible_order:
        return EvaluationReport(
            status="insufficient_labels",
            label_set_version=validation.label_set_version,
            warnings=["No labelled eligible candidates overlap the ranked output."],
        )
    helios_metrics = _metric_set(
        "helios",
        eligible_order,
        label_by_id,
        validation.evaluation_k,
        validation.helios_shortlist_minutes,
    )
    manual_metrics = None
    if validation.manual_candidate_order:
        manual_order = [cid for cid in validation.manual_candidate_order if cid in label_by_id]
        if manual_order:
            manual_metrics = _metric_set(
                "manual_baseline",
                manual_order,
                label_by_id,
                validation.evaluation_k,
                validation.manual_shortlist_minutes,
            )
    baseline_metrics = [
        _metric_set(
            method,
            order,
            label_by_id,
            validation.evaluation_k,
            None,
        )
        for method, order in baseline_orders.items()
        if order
    ]
    deltas: dict[str, float] = {}
    if manual_metrics:
        for field in ("precision_at_k", "recall_at_k", "ndcg_at_k"):
            helios_value = getattr(helios_metrics, field)
            manual_value = getattr(manual_metrics, field)
            if helios_value is not None and manual_value is not None:
                deltas[field] = round(helios_value - manual_value, 6)
        if helios_metrics.shortlist_minutes and manual_metrics.shortlist_minutes:
            deltas["shortlist_minutes"] = round(
                helios_metrics.shortlist_minutes - manual_metrics.shortlist_minutes, 6
            )
    deltas_by_baseline = {
        baseline.method: _metric_deltas(helios_metrics, baseline)
        for baseline in baseline_metrics
    }
    warnings = []
    if len(validation.labels) < 20:
        warnings.append(
            "Small labelled sample: report metrics as hackathon evidence, not general proof."
        )
    if not all(label.blinded for label in validation.labels):
        warnings.append("At least one label was not blinded to the Helios score or rank.")
    if manual_metrics is None:
        warnings.append(
            "Manual baseline order was not supplied; comparative improvement is untested."
        )
    return EvaluationReport(
        status="completed",
        label_set_version=validation.label_set_version,
        helios=helios_metrics,
        manual_baseline=manual_metrics,
        baselines=baseline_metrics,
        deltas=deltas,
        deltas_by_baseline=deltas_by_baseline,
        warnings=warnings,
    )


def _metric_deltas(helios: MetricSet, baseline: MetricSet) -> dict[str, float]:
    deltas: dict[str, float] = {}
    for field in ("precision_at_k", "recall_at_k", "ndcg_at_k"):
        helios_value = getattr(helios, field)
        baseline_value = getattr(baseline, field)
        if helios_value is not None and baseline_value is not None:
            deltas[field] = round(helios_value - baseline_value, 6)
    return deltas


def _metric_set(
    method: str,
    order: list[str],
    labels: dict[str, ValidationDecision],
    requested_k: int,
    shortlist_minutes: float | None,
) -> MetricSet:
    evaluated = [candidate_id for candidate_id in order if candidate_id in labels]
    k = min(requested_k, len(evaluated))
    top = evaluated[:k]
    relevant_total = sum(decision is ValidationDecision.INSPECT for decision in labels.values())
    relevant_top = sum(labels[candidate_id] is ValidationDecision.INSPECT for candidate_id in top)
    precision = relevant_top / k if k else None
    recall = relevant_top / relevant_total if relevant_total else None
    gains = [_gain(labels[candidate_id]) for candidate_id in top]
    ideal_gains = sorted((_gain(decision) for decision in labels.values()), reverse=True)[:k]
    dcg = sum(gain / log2(index + 2) for index, gain in enumerate(gains))
    ideal_dcg = sum(gain / log2(index + 2) for index, gain in enumerate(ideal_gains))
    ndcg = dcg / ideal_dcg if ideal_dcg else None
    return MetricSet(
        method=method,
        evaluated_k=k,
        labelled_candidates=len(labels),
        precision_at_k=round(precision, 6) if precision is not None else None,
        recall_at_k=round(recall, 6) if recall is not None else None,
        ndcg_at_k=round(ndcg, 6) if ndcg is not None else None,
        shortlist_minutes=shortlist_minutes,
    )


def _gain(decision: ValidationDecision) -> int:
    return {
        ValidationDecision.INSPECT: 2,
        ValidationDecision.UNCERTAIN: 1,
        ValidationDecision.REJECT: 0,
    }[decision]
