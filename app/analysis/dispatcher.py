from typing import TypeAlias

from app.analysis.comparison import (
    analyze_intervention_comparison,
)
from app.analysis.distribution import analyze_distribution
from app.analysis.geographic import analyze_geographic_ranking
from app.analysis.models import (
    ComparisonResult,
    DistributionDimension,
    DistributionResult,
    GeographicRankingResult,
    RelationshipNetworkResult,
    TimeTrendResult,
)
from app.analysis.relationship import (
    analyze_intervention_relationships,
)
from app.analysis.time_trend import analyze_time_trend
from app.clinical_trials.normalized_models import NormalizedStudy
from app.schemas.analysis_plan import (
    AnalysisIntent,
    AnalysisPlan,
    ComparisonDimension,
    GroupByDimension,
    NetworkEntity,
)


AnalysisResult: TypeAlias = (
    TimeTrendResult
    | DistributionResult
    | GeographicRankingResult
    | ComparisonResult
    | RelationshipNetworkResult
)


class UnsupportedAnalysisPlanError(ValueError):
    """Raised when a valid plan requests unsupported execution behavior."""


_DISTRIBUTION_DIMENSIONS: dict[
    GroupByDimension,
    DistributionDimension,
] = {
    GroupByDimension.PHASE: DistributionDimension.PHASE,
    GroupByDimension.INTERVENTION_TYPE: (
        DistributionDimension.INTERVENTION_TYPE
    ),
    GroupByDimension.SPONSOR_CATEGORY: (
        DistributionDimension.SPONSOR_CLASS
    ),
}


def run_analysis(
    *,
    plan: AnalysisPlan,
    studies: list[NormalizedStudy],
) -> AnalysisResult:
    """
    Execute the deterministic analyzer selected by an AnalysisPlan.

    The planner interprets language. This dispatcher validates that the
    requested capability is currently supported and invokes deterministic
    analysis code.
    """

    if plan.intent == AnalysisIntent.TIME_TREND:
        return analyze_time_trend(
            studies,
            start_year=plan.filters.start_year,
            end_year=plan.filters.end_year,
        )

    if plan.intent == AnalysisIntent.DISTRIBUTION:
        return _run_distribution(
            plan=plan,
            studies=studies,
        )

    if plan.intent == AnalysisIntent.GEOGRAPHIC_RANKING:
        return analyze_geographic_ranking(
            studies,
            limit=10,
        )

    if plan.intent == AnalysisIntent.COMPARISON:
        return _run_comparison(
            plan=plan,
            studies=studies,
        )

    if plan.intent == AnalysisIntent.RELATIONSHIP_NETWORK:
        return _run_relationship_network(
            plan=plan,
            studies=studies,
        )

    raise UnsupportedAnalysisPlanError(
        f"Unsupported analysis intent: {plan.intent.value}"
    )


def _run_distribution(
    *,
    plan: AnalysisPlan,
    studies: list[NormalizedStudy],
) -> DistributionResult:
    dimension = _DISTRIBUTION_DIMENSIONS.get(plan.group_by)

    if dimension is None:
        raise UnsupportedAnalysisPlanError(
            "Distribution analysis currently supports grouping by phase, "
            "intervention_type, or sponsor_category. Received "
            f"'{plan.group_by.value}'."
        )

    return analyze_distribution(
        studies,
        dimension=dimension,
    )


def _run_comparison(
    *,
    plan: AnalysisPlan,
    studies: list[NormalizedStudy],
) -> ComparisonResult:
    if plan.compare_by != ComparisonDimension.DRUG:
        received = (
            plan.compare_by.value
            if plan.compare_by is not None
            else "none"
        )

        raise UnsupportedAnalysisPlanError(
            "Comparison analysis currently supports only drug comparisons. "
            f"Received '{received}'."
        )

    if len(plan.filters.drug_names) < 2:
        raise UnsupportedAnalysisPlanError(
            "Drug comparison requires at least two drug names."
        )

    return analyze_intervention_comparison(
        studies,
        intervention_names=plan.filters.drug_names,
        start_year=plan.filters.start_year,
        end_year=plan.filters.end_year,
    )


def _run_relationship_network(
    *,
    plan: AnalysisPlan,
    studies: list[NormalizedStudy],
) -> RelationshipNetworkResult:
    network = plan.network

    if network is None:
        raise UnsupportedAnalysisPlanError(
            "Relationship analysis requires a network definition."
        )

    if (
        network.source != NetworkEntity.DRUG
        or network.target != NetworkEntity.DRUG
    ):
        raise UnsupportedAnalysisPlanError(
            "Relationship analysis currently supports only drug-to-drug "
            "co-occurrence networks."
        )

    return analyze_intervention_relationships(
        studies,
        minimum_edge_weight=1,
        max_nodes=25,
    )