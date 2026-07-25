from datetime import date

import pytest

from app.analysis.dispatcher import (
    UnsupportedAnalysisPlanError,
    run_analysis,
)
from app.analysis.models import (
    ComparisonResult,
    TimeTrendResult,
)
from app.clinical_trials.normalized_models import (
    NormalizedIntervention,
    NormalizedInterventionType,
    NormalizedStudy,
)
from app.schemas.analysis_plan import (
    AnalysisFilters,
    AnalysisIntent,
    AnalysisPlan,
    ComparisonDimension,
    GroupByDimension,
    VisualizationType,
)


def build_study(
    *,
    nct_id: str,
    year: int,
    intervention_names: list[str] | None = None,
) -> NormalizedStudy:
    return NormalizedStudy(
        nct_id=nct_id,
        title="Example Study",
        overall_status="COMPLETED",
        start_date=date(year, 1, 1),
        start_date_raw=f"{year}-01-01",
        phases=[],
        conditions=[],
        interventions=[
            NormalizedIntervention(
                name=name,
                intervention_type=NormalizedInterventionType.DRUG,
            )
            for name in (intervention_names or [])
        ],
        lead_sponsor=None,
        countries=[],
    )


def test_dispatches_time_trend_analysis() -> None:
    plan = AnalysisPlan(
        intent=AnalysisIntent.TIME_TREND,
        group_by=GroupByDimension.START_YEAR,
        filters=AnalysisFilters(start_year=2020),
        visualization_type=VisualizationType.TIME_SERIES,
        confidence=0.95,
        reasoning_summary=(
            "The question asks how trial volume changed over time."
        ),
    )

    result = run_analysis(
        plan=plan,
        studies=[
            build_study(
                nct_id="NCT00000001",
                year=2020,
            )
        ],
    )

    assert isinstance(result, TimeTrendResult)
    assert result.points[0].year == 2020
    assert result.points[0].count == 1


def test_dispatches_drug_comparison() -> None:
    plan = AnalysisPlan(
        intent=AnalysisIntent.COMPARISON,
        group_by=GroupByDimension.START_YEAR,
        compare_by=ComparisonDimension.DRUG,
        filters=AnalysisFilters(
            drug_names=[
                "Pembrolizumab",
                "Nivolumab",
            ]
        ),
        visualization_type=VisualizationType.GROUPED_BAR_CHART,
        confidence=0.94,
        reasoning_summary=(
            "The question compares trial volume for two named drugs."
        ),
    )

    studies = [
        build_study(
            nct_id="NCT00000001",
            year=2020,
            intervention_names=["Pembrolizumab"],
        ),
        build_study(
            nct_id="NCT00000002",
            year=2020,
            intervention_names=["Nivolumab"],
        ),
    ]

    result = run_analysis(
        plan=plan,
        studies=studies,
    )

    assert isinstance(result, ComparisonResult)
    assert len(result.series) == 2


def test_rejects_unsupported_condition_comparison() -> None:
    plan = AnalysisPlan(
        intent=AnalysisIntent.COMPARISON,
        group_by=GroupByDimension.START_YEAR,
        compare_by=ComparisonDimension.CONDITION,
        filters=AnalysisFilters(
            conditions=[
                "Melanoma",
                "Lung Cancer",
            ]
        ),
        visualization_type=VisualizationType.GROUPED_BAR_CHART,
        confidence=0.80,
        reasoning_summary=(
            "The question compares two clinical trial conditions."
        ),
    )

    with pytest.raises(
        UnsupportedAnalysisPlanError,
        match="only drug comparisons",
    ):
        run_analysis(
            plan=plan,
            studies=[],
        )