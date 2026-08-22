"""Fuzzy Parameter Project Scheduling ML Challenger Model for Helios.

Inspired by research paper:
"A Heuristic Algorithm for Project Scheduling with Fuzzy Parameters"
(Mohammad Khalilzadeh et al., Procedia Computer Science, 2017).
DOI: 10.1016/j.procs.2017.11.010

This module implements a Machine Learning model for candidate site project scheduling
and ranking under fuzzy parameter uncertainty (e.g. uncertain yield, roof usable area,
grid proximity, cost, and installation duration).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from helios.ranking.contracts import (
    CandidateExplanation,
    DecisionStatus,
    P5RankingRequest,
    RankedCandidate,
    RankingBundle,
)
from helios.ranking.engine import (
    _Candidate,
    _evaluate,
    _exclusion_reasons,
    _join_inputs,
    _pareto_optimal_ids,
    _stability_report,
)
from helios.ranking.features import CRITERIA, FEATURE_DICTIONARY_VERSION

# Attempt scikit-learn import, provide clean pure-python fallback if not installed
try:
    import numpy as np
    from sklearn.ensemble import GradientBoostingRegressor

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


@dataclass(frozen=True)
class TriangularFuzzyNumber:
    """Triangular Fuzzy Number (TFN) representing a fuzzy parameter (l, m, u).

    - l: Lower bound (pessimistic)
    - m: Modal value (most likely)
    - u: Upper bound (optimistic)
    """

    l: float  # noqa: E741
    m: float
    u: float

    def __post_init__(self) -> None:
        if not (self.l <= self.m <= self.u):
            object.__setattr__(self, "l", min(self.l, self.m))
            object.__setattr__(self, "u", max(self.m, self.u))

    def defuzzify(self) -> float:
        """Graded Mean Integration Representation (GMIR) / Centroid defuzzification."""
        return (self.l + 4.0 * self.m + self.u) / 6.0

    def alpha_cut(self, alpha: float) -> tuple[float, float]:
        """Compute the [lower, upper] interval for a given alpha cut level (0 <= alpha <= 1)."""
        alpha_clamped = max(0.0, min(1.0, alpha))
        lower = self.l + alpha_clamped * (self.m - self.l)
        upper = self.u - alpha_clamped * (self.u - self.m)
        return (lower, upper)

    def add(self, other: TriangularFuzzyNumber) -> TriangularFuzzyNumber:
        return TriangularFuzzyNumber(self.l + other.l, self.m + other.m, self.u + other.u)

    def scale(self, factor: float) -> TriangularFuzzyNumber:
        if factor >= 0:
            return TriangularFuzzyNumber(self.l * factor, self.m * factor, self.u * factor)
        return TriangularFuzzyNumber(self.u * factor, self.m * factor, self.l * factor)


@dataclass
class FuzzyProjectCandidate:
    """Project candidate represented with fuzzy parameters and schedule duration."""

    candidate: _Candidate

    # Fuzzy criterion values
    fuzzy_generation: TriangularFuzzyNumber
    fuzzy_physical: TriangularFuzzyNumber
    fuzzy_grid: TriangularFuzzyNumber
    fuzzy_economics: TriangularFuzzyNumber

    # Fuzzy project scheduling parameters
    fuzzy_duration_days: TriangularFuzzyNumber
    fuzzy_risk_index: float
    defuzzified_utility: float


def create_fuzzy_candidate(
    candidate: _Candidate,
    weights: dict[str, float],
) -> FuzzyProjectCandidate:
    """Fuzzify candidate criterion scores using confidence-sized uncertainty spans."""

    def _make_tfn(val: float, conf: float) -> TriangularFuzzyNumber:
        half_span = 0.20 * (1.0 - conf)
        lower = max(0.0, val - half_span)
        upper = min(1.0, val + half_span)
        return TriangularFuzzyNumber(lower, val, upper)

    conf_dict = candidate.confidence
    gen_conf = conf_dict.get("generation", candidate.overall_confidence)
    phys_conf = conf_dict.get("physical", candidate.overall_confidence)
    grid_conf = conf_dict.get("grid", candidate.overall_confidence)
    econ_conf = conf_dict.get("economics", candidate.overall_confidence)

    f_gen = _make_tfn(candidate.values["generation"], gen_conf)
    f_phys = _make_tfn(candidate.values["physical"], phys_conf)
    f_grid = _make_tfn(candidate.values["grid"], grid_conf)
    f_econ = _make_tfn(candidate.values["economics"], econ_conf)

    # Calculate fuzzy project installation duration (days)
    p2 = candidate.p2
    base_duration = 5.0 + (p2.usable_area_m2 / 500.0) + (p2.grid_distance_m / 200.0)
    dur_conf = candidate.overall_confidence
    dur_span = base_duration * 0.25 * (1.0 - dur_conf)
    f_duration = TriangularFuzzyNumber(
        max(1.0, base_duration - dur_span),
        base_duration,
        base_duration + dur_span * 1.5,
    )

    w_gen = weights.get("generation", 0.35)
    w_phys = weights.get("physical", 0.30)
    w_grid = weights.get("grid", 0.20)
    w_econ = weights.get("economics", 0.15)

    fuzzy_total = (
        f_gen.scale(w_gen)
        .add(f_phys.scale(w_phys))
        .add(f_grid.scale(w_grid))
        .add(f_econ.scale(w_econ))
    )

    defuzz_val = fuzzy_total.defuzzify()
    risk_index = (fuzzy_total.u - fuzzy_total.l) / (2.0 * max(0.01, fuzzy_total.m))

    return FuzzyProjectCandidate(
        candidate=candidate,
        fuzzy_generation=f_gen,
        fuzzy_physical=f_phys,
        fuzzy_grid=f_grid,
        fuzzy_economics=f_econ,
        fuzzy_duration_days=f_duration,
        fuzzy_risk_index=risk_index,
        defuzzified_utility=defuzz_val,
    )


class PurePythonFuzzyRanker:
    """Surrogate decision ensemble ranker when scikit-learn is omitted."""

    def predict_score(self, features: list[float]) -> float:
        defuzz_u, gen_m, phys_m, grid_m, econ_m, conf, dur_m, risk = features[:8]
        base = 0.40 * defuzz_u + 0.25 * gen_m + 0.15 * phys_m + 0.10 * grid_m + 0.10 * econ_m
        confidence_penalty = 0.05 * (1.0 - conf)
        risk_penalty = 0.05 * risk
        schedule_bonus = 0.02 * math.exp(-dur_m / 30.0)
        return max(0.0, min(1.0, base - confidence_penalty - risk_penalty + schedule_bonus))


class FuzzyMLProjectScheduler:
    """ML Challenger Model for fuzzy parameter project candidate scheduling & ranking."""

    def __init__(self) -> None:
        self.model_version = "fuzzy_ml_scheduler_v1"
        self._sklearn_model: Any | None = None
        self._pure_ranker = PurePythonFuzzyRanker()
        self._is_trained = False

    def extract_features(
        self, candidate: FuzzyProjectCandidate, weights: dict[str, float]
    ) -> list[float]:
        return [
            candidate.defuzzified_utility,
            candidate.fuzzy_generation.m,
            candidate.fuzzy_physical.m,
            candidate.fuzzy_grid.m,
            candidate.fuzzy_economics.m,
            candidate.candidate.overall_confidence,
            candidate.fuzzy_duration_days.m,
            candidate.fuzzy_risk_index,
            candidate.fuzzy_generation.u - candidate.fuzzy_generation.l,
            candidate.fuzzy_physical.u - candidate.fuzzy_physical.l,
            weights.get("generation", 0.35),
            weights.get("physical", 0.30),
        ]

    def fit_synthetic_model(self) -> None:
        if HAS_SKLEARN:
            rng = np.random.RandomState(42)
            X_train = rng.uniform(0.0, 1.0, (200, 12))
            y_train = (
                0.4 * X_train[:, 0]
                + 0.3 * X_train[:, 1]
                + 0.2 * X_train[:, 5]
                - 0.1 * X_train[:, 7]
            )
            gbr = GradientBoostingRegressor(n_estimators=50, random_state=42, max_depth=3)
            gbr.fit(X_train, y_train)
            self._sklearn_model = gbr
        self._is_trained = True

    def predict_priority_score(
        self, candidate: FuzzyProjectCandidate, weights: dict[str, float]
    ) -> float:
        feats = self.extract_features(candidate, weights)
        if HAS_SKLEARN and self._sklearn_model is not None:
            X = np.array([feats])
            score = float(self._sklearn_model.predict(X)[0])
            return max(0.0, min(1.0, score))
        return self._pure_ranker.predict_score(feats)


def rank_candidates_fuzzy_ml(request: P5RankingRequest) -> RankingBundle:
    """Run candidate screening, fuzzy parameter transformation, and ML project scheduling."""

    joined = _join_inputs(request)
    exclusions = {
        candidate.candidate_id: _exclusion_reasons(candidate, request)
        for candidate in joined
    }
    eligible = [c for c in joined if not exclusions[c.candidate_id]]
    weights = request.weights.model_dump()

    fuzzy_candidates = [create_fuzzy_candidate(c, weights) for c in eligible]

    scheduler = FuzzyMLProjectScheduler()
    scheduler.fit_synthetic_model()

    ml_scores = {
        fc.candidate.candidate_id: scheduler.predict_priority_score(fc, weights)
        for fc in fuzzy_candidates
    }

    nominal_order = sorted(
        eligible, key=lambda c: (-ml_scores[c.candidate_id], c.candidate_id)
    )
    nominal_ranks = {
        c.candidate_id: index for index, c in enumerate(nominal_order, 1)
    }

    pareto_ids = _pareto_optimal_ids(eligible)
    stability, robust_ranks = _stability_report(eligible, nominal_ranks, request)
    stability_by_id = {row.candidate_id: row for row in stability.candidates}

    ranked_candidates: list[RankedCandidate] = []
    explanations: list[CandidateExplanation] = []

    for candidate in joined:
        cid = candidate.candidate_id
        is_eligible = not exclusions[cid]

        if is_eligible:
            raw_vals = candidate.values
            weights_sum = sum(weights.get(k, 0.25) for k in CRITERIA)
            w_norm = {k: weights.get(k, 0.25) / weights_sum for k in CRITERIA}
            contributions = {k: raw_vals[k] * w_norm[k] for k in CRITERIA}
            nom_score = sum(contributions.values())
            status = stability_by_id[cid].decision_status

            ranked_candidates.append(
                RankedCandidate(
                    candidate_id=cid,
                    geometry=candidate.p2.geometry,
                    eligible=True,
                    exclusion_reasons=[],
                    rank=nominal_ranks[cid],
                    nominal_rank=nominal_ranks[cid],
                    robust_rank=robust_ranks[cid],
                    nominal_score=nom_score,
                    component_contributions=contributions,
                    overall_confidence=candidate.overall_confidence,
                    pareto_optimal=cid in pareto_ids,
                    decision_status=status,
                )
            )

            fc = next(f for f in fuzzy_candidates if f.candidate.candidate_id == cid)
            positive_reasons = ["Fuzzy ML Priority Model: " + str(round(ml_scores[cid], 3))]
            caution_reasons = (
                ["HIGH_SCHEDULE_RISK"] if fc.fuzzy_risk_index > 0.40 else []
            )

            summary_text = (
                f"Candidate {cid} ranked #{nominal_ranks[cid]} by Fuzzy ML Scheduler "
                f"(Score: {ml_scores[cid]:.3f}, Est: ~{fc.fuzzy_duration_days.m:.1f}d)."
            )

            explanations.append(
                CandidateExplanation(
                    candidate_id=cid,
                    positive_reasons=positive_reasons,
                    caution_reasons=caution_reasons,
                    trace={
                        "fuzzy_generation": round(fc.fuzzy_generation.defuzzify(), 4),
                        "fuzzy_physical": round(fc.fuzzy_physical.defuzzify(), 4),
                        "fuzzy_grid": round(fc.fuzzy_grid.defuzzify(), 4),
                        "fuzzy_economics": round(fc.fuzzy_economics.defuzzify(), 4),
                        "fuzzy_schedule_duration_days": round(fc.fuzzy_duration_days.m, 1),
                        "fuzzy_risk_index": round(fc.fuzzy_risk_index, 4),
                        "summary": summary_text,
                    },
                )
            )
        else:
            cautions = [str(r.value if hasattr(r, "value") else r) for r in exclusions[cid]]
            ranked_candidates.append(
                RankedCandidate(
                    candidate_id=cid,
                    geometry=candidate.p2.geometry,
                    eligible=False,
                    exclusion_reasons=exclusions[cid],
                    rank=None,
                    nominal_rank=None,
                    robust_rank=None,
                    nominal_score=None,
                    component_contributions={},
                    overall_confidence=candidate.overall_confidence,
                    pareto_optimal=None,
                    decision_status=DecisionStatus.EXCLUDED,
                )
            )
            explanations.append(
                CandidateExplanation(
                    candidate_id=cid,
                    positive_reasons=[],
                    caution_reasons=cautions,
                    trace={
                        "summary": f"Excluded due to criteria violations: {exclusions[cid]}."
                    },
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
            c.candidate_id
            for c in sorted(
                eligible, key=lambda row: (-row.values["generation"], row.candidate_id)
            )
        ],
        "equal_weight_mcda": [
            c.candidate_id
            for c in sorted(
                eligible, key=lambda row: (-sum(row.values.values()) / 4.0, row.candidate_id)
            )
        ],
        "balanced_nominal_mcda": [c.candidate_id for c in nominal_order],
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
