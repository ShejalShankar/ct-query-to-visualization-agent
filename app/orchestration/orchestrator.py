from collections.abc import Awaitable
from typing import Protocol

from app.analysis.dispatcher import run_analysis
from app.clinical_trials.models import StudySearchResult
from app.clinical_trials.normalizer import normalize_studies
from app.schemas.analysis_plan import (
    AnalysisFilters,
    AnalysisPlan,
)
from app.schemas.request import VisualizationRequest
from app.schemas.response import VisualizationResponse
from app.visualization.builder import build_visualization_response


class PlannerProtocol(Protocol):
    def create_plan(
        self,
        query: str,
    ) -> Awaitable[AnalysisPlan]:
        """Convert a user query into a typed analysis plan."""


class ClinicalTrialsClientProtocol(Protocol):
    def search_studies(
        self,
        *,
        query_term: str,
        max_studies: int,
    ) -> Awaitable[StudySearchResult]:
        """Retrieve matching studies from ClinicalTrials.gov."""


class VisualizationOrchestrator:
    """
    Coordinate the query-to-visualization workflow.

    The orchestrator owns sequencing only. Natural-language interpretation,
    API retrieval, normalization, deterministic analysis, and response
    formatting remain delegated to their respective components.
    """

    def __init__(
        self,
        *,
        planner: PlannerProtocol,
        clinical_trials_client: ClinicalTrialsClientProtocol,
    ) -> None:
        self._planner = planner
        self._clinical_trials_client = clinical_trials_client

    async def run(
        self,
        request: VisualizationRequest,
    ) -> VisualizationResponse:
        planned_analysis = await self._planner.create_plan(
            request.query
        )

        analysis_plan = _apply_request_overrides(
            plan=planned_analysis,
            request=request,
        )

        search_query = _build_search_query(
            request=request,
            plan=analysis_plan,
        )

        search_result = (
            await self._clinical_trials_client.search_studies(
                query_term=search_query,
                max_studies=request.max_studies,
            )
        )

        normalization_result = normalize_studies(
            search_result.studies
        )

        analysis_result = run_analysis(
            plan=analysis_plan,
            studies=normalization_result.studies,
        )

        response = build_visualization_response(
            query=request.query,
            plan=analysis_plan,
            result=analysis_result,
            studies=normalization_result.studies,
            filters_applied=_extract_applied_filters(
                analysis_plan.filters
            ),
            partial_results=search_result.partial_results,
            citation_limit=request.max_citations_per_datum,
        )

        _add_normalization_metadata(
            response=response,
            normalization_warning_messages=[
                warning.message
                for warning in normalization_result.warnings
            ],
            skipped_count=normalization_result.skipped_count,
        )

        if not request.include_citations:
            _remove_citations(response)

        return response


def _apply_request_overrides(
    *,
    plan: AnalysisPlan,
    request: VisualizationRequest,
) -> AnalysisPlan:
    """
    Merge explicit structured request fields into the LLM-produced plan.

    Empty request fields do not erase values inferred by the planner. When the
    caller explicitly supplies a value, that value is authoritative.
    """

    planned_filters = plan.filters

    merged_filters = AnalysisFilters(
        drug_names=(
            request.drug_names
            if request.drug_names
            else planned_filters.drug_names
        ),
        conditions=(
            request.conditions
            if request.conditions
            else planned_filters.conditions
        ),
        phases=(
            request.phases
            if request.phases
            else planned_filters.phases
        ),
        sponsors=(
            request.sponsors
            if request.sponsors
            else planned_filters.sponsors
        ),
        countries=(
            request.countries
            if request.countries
            else planned_filters.countries
        ),
        recruitment_statuses=(
            request.recruitment_statuses
            if request.recruitment_statuses
            else planned_filters.recruitment_statuses
        ),
        start_year=(
            request.start_year
            if request.start_year is not None
            else planned_filters.start_year
        ),
        end_year=(
            request.end_year
            if request.end_year is not None
            else planned_filters.end_year
        ),
    )

    return plan.model_copy(
        update={
            "filters": merged_filters,
        }
    )


def _build_search_query(
    *,
    request: VisualizationRequest,
    plan: AnalysisPlan,
) -> str:
    """
    Produce a concise ClinicalTrials.gov search expression.

    Entity filters are preferred because they are less ambiguous than the
    full analytical question. The original query is retained as a fallback.
    """

    search_terms: list[str] = []

    search_terms.extend(plan.filters.drug_names)
    search_terms.extend(plan.filters.conditions)
    search_terms.extend(plan.filters.sponsors)

    unique_terms: list[str] = []
    seen: set[str] = set()

    for term in search_terms:
        cleaned = term.strip()
        comparison_key = cleaned.casefold()

        if not cleaned or comparison_key in seen:
            continue

        seen.add(comparison_key)
        unique_terms.append(cleaned)

    if not unique_terms:
        return request.query

    return " AND ".join(
        f'"{term}"'
        for term in unique_terms
    )


def _extract_applied_filters(
    filters: AnalysisFilters,
) -> dict[str, object]:
    raw_filters = filters.model_dump(mode="json")

    return {
        key: value
        for key, value in raw_filters.items()
        if value not in (None, [], {})
    }


def _add_normalization_metadata(
    *,
    response: VisualizationResponse,
    normalization_warning_messages: list[str],
    skipped_count: int,
) -> None:
    if skipped_count:
        response.meta.warnings.append(
            f"{skipped_count} retrieved studies were skipped during "
            "normalization."
        )

    for message in normalization_warning_messages:
        if message not in response.meta.warnings:
            response.meta.warnings.append(message)


def _remove_citations(
    response: VisualizationResponse,
) -> None:
    response.citations = {}

    if response.visualization.data is not None:
        for datum in response.visualization.data:
            datum.citation_ref = None

    if response.visualization.nodes is not None:
        for node in response.visualization.nodes:
            node.citation_ref = None

    if response.visualization.edges is not None:
        for edge in response.visualization.edges:
            edge.citation_ref = None