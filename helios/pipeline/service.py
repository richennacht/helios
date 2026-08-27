from uuid import uuid4

from helios.contracts.models import (
    AnalysisRequest,
    AnalysisRun,
    CandidateResult,
    RerankRequest,
    RunStatus,
    TemporalType,
)
from helios.explanations.templates import explain
from helios.ranking.scoring import component_scores, exclusion_reasons, total_score
from helios.storage.repository import InMemoryRunRepository


class AnalysisService:
    def __init__(self, repository: InMemoryRunRepository | None = None) -> None:
        self.repository = repository or InMemoryRunRepository()

    def create(self, request: AnalysisRequest) -> AnalysisRun:
        candidate_ids = [candidate.candidate_id for candidate in request.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("Duplicate candidate_id found in analysis request")
        results = self._rank(request.candidates, request.scenario, request.weights)
        run = AnalysisRun(
            run_id=str(uuid4()),
            status=RunStatus.COMPLETED,
            region_name=request.region_name,
            reference_date=request.reference_date,
            scenario=request.scenario,
            weights=request.weights,
            source_ids=[source.source_id for source in request.sources],
            temporal_warnings=self._temporal_warnings(request),
            candidates=results,
        )
        return self.repository.save(run)

    def get(self, run_id: str) -> AnalysisRun | None:
        return self.repository.get(run_id)

    def rerank(self, run_id: str, request: RerankRequest) -> AnalysisRun | None:
        run = self.repository.get(run_id)
        if run is None:
            return None
        candidates = [
            self._candidate_from_result(candidate) for candidate in run.candidates
        ]
        run.weights = request.weights
        run.candidates = self._rank(candidates, run.scenario, request.weights)
        return self.repository.save(run)

    def as_geojson(self, run_id: str) -> dict | None:
        run = self.repository.get(run_id)
        if run is None:
            return None
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": candidate.geometry,
                    "properties": {
                        "run_id": run.run_id,
                        "candidate_id": candidate.candidate_id,
                        "name": candidate.name,
                        "eligible": candidate.eligible,
                        "rank": candidate.rank,
                        "total_score": candidate.total_score,
                        "confidence": candidate.normalized.confidence,
                        "positive_reasons": candidate.positive_reasons,
                        "caution_reasons": candidate.caution_reasons,
                    },
                }
                for candidate in run.candidates
            ],
        }

    @staticmethod
    def _rank(candidates, scenario, weights) -> list[CandidateResult]:
        results: list[CandidateResult] = []
        for candidate in candidates:
            exclusions = exclusion_reasons(candidate, scenario)
            eligible = not exclusions
            components = component_scores(candidate, weights) if eligible else {}
            positives, cautions = explain(candidate)
            results.append(
                CandidateResult(
                    candidate_id=candidate.candidate_id,
                    name=candidate.name,
                    geometry=candidate.geometry,
                    metrics=candidate.metrics,
                    normalized=candidate.normalized,
                    eligible=eligible,
                    exclusion_reasons=exclusions,
                    component_scores=components,
                    total_score=total_score(components) if eligible else None,
                    rank=None,
                    positive_reasons=positives if eligible else [],
                    caution_reasons=cautions,
                )
            )
        eligible_results = sorted(
            (result for result in results if result.eligible),
            key=lambda result: result.total_score or 0,
            reverse=True,
        )
        for index, result in enumerate(eligible_results, start=1):
            result.rank = index
        return sorted(results, key=lambda result: (not result.eligible, result.rank or 10**9))

    @staticmethod
    def _candidate_from_result(result):
        from helios.contracts.models import CandidateInput

        return CandidateInput(
            candidate_id=result.candidate_id,
            name=result.name,
            geometry=result.geometry,
            metrics=result.metrics,
            normalized=result.normalized,
        )

    @staticmethod
    def _temporal_warnings(request: AnalysisRequest) -> list[str]:
        warnings: list[str] = []
        for source in request.sources:
            if source.temporal_type in {TemporalType.SNAPSHOT, TemporalType.RANGE}:
                if source.valid_from and request.reference_date < source.valid_from:
                    warnings.append(f"{source.source_id}: reference date precedes validity")
                if source.valid_to and request.reference_date > source.valid_to:
                    warnings.append(f"{source.source_id}: reference date exceeds validity")
        return warnings
