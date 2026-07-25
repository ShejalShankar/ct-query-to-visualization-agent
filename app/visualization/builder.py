from datetime import UTC, datetime
from typing import Any, TypeAlias

from app.analysis.models import (
    ComparisonResult,
    DistributionResult,
    GeographicRankingResult,
    RelationshipNetworkResult,
    TimeTrendResult,
)
from app.clinical_trials.normalized_models import NormalizedStudy
from app.schemas.analysis_plan import (
    AnalysisIntent,
    AnalysisPlan,
    GroupByDimension,
    NetworkEntity,
    VisualizationType,
)
from app.schemas.response import (
    ChartDatum,
    CitationGroup as ResponseCitationGroup,
    CitationRecord,
    NetworkEdge as ResponseNetworkEdge,
    NetworkNode as ResponseNetworkNode,
    ResponseMetadata,
    VisualizationChannel,
    VisualizationResponse,
    VisualizationSpecification,
)


AnalysisResult: TypeAlias = (
    TimeTrendResult
    | DistributionResult
    | GeographicRankingResult
    | ComparisonResult
    | RelationshipNetworkResult
)


def build_visualization_response(
    *,
    query: str,
    plan: AnalysisPlan,
    result: AnalysisResult,
    studies: list[NormalizedStudy],
    filters_applied: dict[str, Any] | None = None,
    partial_results: bool = False,
    citation_limit: int = 5,
) -> VisualizationResponse:
    """
    Convert a typed analysis result into the public visualization response.

    Analysis functions remain independent of chart formatting and API response
    concerns. This builder is the adapter between the analysis and API layers.
    """

    if citation_limit <= 0:
        raise ValueError("citation_limit must be greater than zero")

    _validate_result_matches_plan(plan, result)

    study_by_nct_id = {
        study.nct_id: study
        for study in studies
    }

    citations = _build_citations(
        result=result,
        study_by_nct_id=study_by_nct_id,
        citation_limit=citation_limit,
    )

    visualization = _build_specification(
        plan=plan,
        result=result,
    )

    metadata = ResponseMetadata(
        generated_at=datetime.now(UTC),
        query=query,
        analysis_plan=plan,
        filters_applied=(
            filters_applied
            if filters_applied is not None
            else _extract_applied_filters(plan)
        ),
        records_matched=result.total_studies,
        records_used=result.included_studies,
        records_excluded=result.excluded_studies,
        assumptions=_build_assumptions(result),
        warnings=list(result.warnings),
        partial_results=partial_results,
    )

    return VisualizationResponse(
        visualization=visualization,
        meta=metadata,
        citations=citations,
    )


def _build_specification(
    *,
    plan: AnalysisPlan,
    result: AnalysisResult,
) -> VisualizationSpecification:
    if isinstance(result, TimeTrendResult):
        return _build_time_trend_specification(plan, result)

    if isinstance(result, DistributionResult):
        return _build_distribution_specification(plan, result)

    if isinstance(result, GeographicRankingResult):
        return _build_geographic_specification(plan, result)

    if isinstance(result, ComparisonResult):
        return _build_comparison_specification(plan, result)

    if isinstance(result, RelationshipNetworkResult):
        return _build_relationship_specification(plan, result)

    raise TypeError(
        f"Unsupported analysis result type: {type(result).__name__}"
    )


def _build_time_trend_specification(
    plan: AnalysisPlan,
    result: TimeTrendResult,
) -> VisualizationSpecification:
    data = [
        ChartDatum(
            datum_id=f"year:{point.year}",
            citation_ref=f"year:{point.year}",
            year=point.year,
            trial_count=point.count,
        )
        for point in result.points
    ]

    return VisualizationSpecification(
        type=VisualizationType.TIME_SERIES,
        title=_time_trend_title(plan),
        description=(
            "Number of matching clinical studies grouped by study start year."
        ),
        encoding={
            "x": VisualizationChannel(
                field="year",
                data_type="temporal",
                label="Start year",
            ),
            "y": VisualizationChannel(
                field="trial_count",
                data_type="quantitative",
                label="Number of trials",
                unit="trials",
            ),
        },
        data=data,
    )


def _build_distribution_specification(
    plan: AnalysisPlan,
    result: DistributionResult,
) -> VisualizationSpecification:
    dimension_field = result.dimension.value

    data = [
        ChartDatum(
            datum_id=f"{dimension_field}:{_slug(point.category)}",
            citation_ref=point.category,
            category=point.category,
            trial_count=point.count,
        )
        for point in result.points
    ]

    return VisualizationSpecification(
        type=VisualizationType.BAR_CHART,
        title=f"Clinical Trial Distribution by {_humanize(dimension_field)}",
        description=(
            f"Number of matching studies grouped by "
            f"{_humanize(dimension_field).lower()}."
        ),
        encoding={
            "x": VisualizationChannel(
                field="category",
                data_type="nominal",
                label=_humanize(dimension_field),
            ),
            "y": VisualizationChannel(
                field="trial_count",
                data_type="quantitative",
                label="Number of trials",
                unit="trials",
            ),
        },
        data=data,
    )


def _build_geographic_specification(
    plan: AnalysisPlan,
    result: GeographicRankingResult,
) -> VisualizationSpecification:
    data = [
        ChartDatum(
            datum_id=f"country:{_slug(point.country)}",
            citation_ref=point.country,
            country=point.country,
            trial_count=point.count,
            rank=index,
        )
        for index, point in enumerate(result.points, start=1)
    ]

    return VisualizationSpecification(
        type=VisualizationType.BAR_CHART,
        title="Countries Ranked by Number of Clinical Trials",
        description=(
            "Countries ranked by the number of matching studies with at "
            "least one reported study location."
        ),
        encoding={
            "x": VisualizationChannel(
                field="country",
                data_type="nominal",
                label="Country",
            ),
            "y": VisualizationChannel(
                field="trial_count",
                data_type="quantitative",
                label="Number of trials",
                unit="trials",
            ),
        },
        data=data,
    )


def _build_comparison_specification(
    plan: AnalysisPlan,
    result: ComparisonResult,
) -> VisualizationSpecification:
    data: list[ChartDatum] = []

    for series in result.series:
        for point in series.points:
            citation_ref = f"{series.label}:{point.year}"

            data.append(
                ChartDatum(
                    datum_id=(
                        f"series:{_slug(series.label)}:year:{point.year}"
                    ),
                    citation_ref=(
                        citation_ref
                        if _has_citation(result, citation_ref)
                        else None
                    ),
                    year=point.year,
                    comparison_group=series.label,
                    trial_count=point.count,
                )
            )

    return VisualizationSpecification(
        type=VisualizationType.GROUPED_BAR_CHART,
        title=_comparison_title(plan, result),
        description=(
            "Matching studies compared by intervention and study start year."
        ),
        encoding={
            "x": VisualizationChannel(
                field="year",
                data_type="temporal",
                label="Start year",
            ),
            "y": VisualizationChannel(
                field="trial_count",
                data_type="quantitative",
                label="Number of trials",
                unit="trials",
            ),
            "series": VisualizationChannel(
                field="comparison_group",
                data_type="nominal",
                label="Intervention",
            ),
        },
        data=data,
    )


def _build_relationship_specification(
    plan: AnalysisPlan,
    result: RelationshipNetworkResult,
) -> VisualizationSpecification:
    network = plan.network

    if (
        network is None
        or network.source != NetworkEntity.DRUG
        or network.target != NetworkEntity.DRUG
    ):
        raise ValueError(
            "The current relationship analyzer supports only drug-to-drug "
            "co-occurrence networks."
        )

    nodes = [
        ResponseNetworkNode(
            id=node.id,
            label=node.label,
            entity_type="drug",
            weight=node.study_count,
        )
        for node in result.nodes
    ]

    edges = [
        ResponseNetworkEdge(
            id=f"{edge.source}|{edge.target}",
            source=edge.source,
            target=edge.target,
            weight=edge.weight,
            citation_ref=f"{edge.source}|{edge.target}",
        )
        for edge in result.edges
    ]

    return VisualizationSpecification(
        type=VisualizationType.NETWORK_GRAPH,
        title="Clinical Trial Intervention Co-occurrence Network",
        description=(
            "Interventions are connected when they appear in the same study. "
            "Relationship weight is the number of supporting studies."
        ),
        encoding={
            "source": VisualizationChannel(
                field="source",
                data_type="nominal",
                label="Source intervention",
            ),
            "target": VisualizationChannel(
                field="target",
                data_type="nominal",
                label="Target intervention",
            ),
            "weight": VisualizationChannel(
                field="weight",
                data_type="quantitative",
                label="Shared studies",
                unit="studies",
            ),
        },
        nodes=nodes,
        edges=edges,
    )


def _build_citations(
    *,
    result: AnalysisResult,
    study_by_nct_id: dict[str, NormalizedStudy],
    citation_limit: int,
) -> dict[str, ResponseCitationGroup]:
    citation_field = _citation_field_for_result(result)
    response: dict[str, ResponseCitationGroup] = {}

    for citation_group in result.citations:
        existing_nct_ids = [
            nct_id
            for nct_id in citation_group.nct_ids
            if nct_id in study_by_nct_id
        ]

        returned_nct_ids = existing_nct_ids[:citation_limit]

        records = [
            CitationRecord(
                nct_id=nct_id,
                field=citation_field,
                excerpt=_citation_excerpt(
                    result=result,
                    study=study_by_nct_id[nct_id],
                ),
            )
            for nct_id in returned_nct_ids
        ]

        response[citation_group.key] = ResponseCitationGroup(
            total_records=len(existing_nct_ids),
            records_returned=len(records),
            truncated=len(records) < len(existing_nct_ids),
            records=records,
        )

    return response


def _citation_field_for_result(result: AnalysisResult) -> str:
    if isinstance(result, TimeTrendResult):
        return "normalized.start_date"

    if isinstance(result, DistributionResult):
        return f"normalized.{result.dimension.value}"

    if isinstance(result, GeographicRankingResult):
        return "normalized.countries"

    if isinstance(result, ComparisonResult):
        return "normalized.interventions.name, normalized.start_date"

    if isinstance(result, RelationshipNetworkResult):
        return "normalized.interventions.name"

    raise TypeError(
        f"Unsupported analysis result type: {type(result).__name__}"
    )


def _citation_excerpt(
    *,
    result: AnalysisResult,
    study: NormalizedStudy,
) -> str:
    if isinstance(result, TimeTrendResult):
        return (
            study.start_date.isoformat()
            if study.start_date is not None
            else study.nct_id
        )

    if isinstance(result, DistributionResult):
        return _distribution_excerpt(result, study)

    if isinstance(result, GeographicRankingResult):
        return ", ".join(study.countries) or study.nct_id

    if isinstance(
        result,
        (ComparisonResult, RelationshipNetworkResult),
    ):
        intervention_names = [
            intervention.name
            for intervention in study.interventions
        ]

        return ", ".join(intervention_names) or study.nct_id

    return study.nct_id


def _distribution_excerpt(
    result: DistributionResult,
    study: NormalizedStudy,
) -> str:
    dimension = result.dimension.value

    if dimension == "phase":
        return ", ".join(
            phase.value if hasattr(phase, "value") else str(phase)
            for phase in study.phases
        ) or study.nct_id

    if dimension == "overall_status":
        return str(study.overall_status)

    if dimension == "sponsor_class":
        if study.lead_sponsor is None:
            return study.nct_id

        sponsor_class = study.lead_sponsor.sponsor_class
        return (
            sponsor_class.value
            if hasattr(sponsor_class, "value")
            else str(sponsor_class)
        )

    if dimension == "intervention_type":
        values = [
            (
                intervention.intervention_type.value
                if hasattr(intervention.intervention_type, "value")
                else str(intervention.intervention_type)
            )
            for intervention in study.interventions
        ]
        return ", ".join(values) or study.nct_id

    return study.nct_id


def _validate_result_matches_plan(
    plan: AnalysisPlan,
    result: AnalysisResult,
) -> None:
    expected_result_by_intent: dict[AnalysisIntent, type[object]] = {
        AnalysisIntent.TIME_TREND: TimeTrendResult,
        AnalysisIntent.DISTRIBUTION: DistributionResult,
        AnalysisIntent.COMPARISON: ComparisonResult,
        AnalysisIntent.GEOGRAPHIC_RANKING: GeographicRankingResult,
        AnalysisIntent.RELATIONSHIP_NETWORK: RelationshipNetworkResult,
    }

    expected_type = expected_result_by_intent[plan.intent]

    if not isinstance(result, expected_type):
        raise ValueError(
            f"Plan intent '{plan.intent.value}' requires "
            f"{expected_type.__name__}, received "
            f"{type(result).__name__}."
        )


def _extract_applied_filters(plan: AnalysisPlan) -> dict[str, Any]:
    raw_filters = plan.filters.model_dump(mode="json")

    return {
        key: value
        for key, value in raw_filters.items()
        if value not in (None, [], {})
    }


def _build_assumptions(result: AnalysisResult) -> list[str]:
    if isinstance(result, TimeTrendResult):
        return [
            "Studies were grouped using their normalized study start date."
        ]

    if isinstance(result, DistributionResult):
        if result.assignment_count > result.included_studies:
            return [
                "A study may contribute to multiple categories when the "
                "selected field contains multiple values."
            ]

        return []

    if isinstance(result, GeographicRankingResult):
        if result.country_assignments > result.included_studies:
            return [
                "A multi-country study contributes once to each distinct "
                "reported country."
            ]

        return []

    if isinstance(result, ComparisonResult):
        return [
            "Comparison membership uses case-insensitive exact matching "
            "against normalized intervention names."
        ]

    if isinstance(result, RelationshipNetworkResult):
        return [
            "An edge represents two interventions appearing in the same "
            "clinical study."
        ]

    return []


def _time_trend_title(plan: AnalysisPlan) -> str:
    drug_names = plan.filters.drug_names

    if drug_names:
        return f"{', '.join(drug_names)} Trials Started by Year"

    return "Clinical Trials Started by Year"


def _comparison_title(
    plan: AnalysisPlan,
    result: ComparisonResult,
) -> str:
    labels = [
        series.label
        for series in result.series
    ]

    if labels:
        return f"{' vs. '.join(labels)} Trials by Start Year"

    return "Clinical Trial Comparison by Start Year"


def _has_citation(
    result: ComparisonResult,
    key: str,
) -> bool:
    return any(
        citation.key == key
        for citation in result.citations
    )


def _humanize(value: str) -> str:
    return value.replace("_", " ").title()


def _slug(value: str) -> str:
    return "-".join(value.casefold().split())