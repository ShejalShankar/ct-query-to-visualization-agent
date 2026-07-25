from datetime import date

from app.analysis.models import (
    CitationGroup,
    TimeTrendPoint,
    TimeTrendResult,
)
from app.clinical_trials.normalized_models import NormalizedStudy
from app.schemas.analysis_plan import (
    AnalysisFilters,
    AnalysisIntent,
    AnalysisPlan,
    GroupByDimension,
    VisualizationType,
)
from app.visualization.builder import build_visualization_response


def test_builds_time_trend_visualization_response():
    study = NormalizedStudy(
        nct_id="NCT00000001",
        title="Example Study",
        overall_status="COMPLETED",
        start_date=date(2020, 1, 1),
        start_date_raw="2020-01-01",
        phases=[],
        conditions=[],
        interventions=[],
        lead_sponsor=None,
        countries=[],
    )

    plan = AnalysisPlan(
        intent=AnalysisIntent.TIME_TREND,
        group_by=GroupByDimension.START_YEAR,
        filters=AnalysisFilters(
            drug_names=["Pembrolizumab"],
            start_year=2020,
        ),
        visualization_type=VisualizationType.TIME_SERIES,
        confidence=0.95,
        reasoning_summary=(
            "The query asks how trial volume changed over time."
        ),
    )

    result = TimeTrendResult(
        points=[
            TimeTrendPoint(
                year=2020,
                count=1,
            )
        ],
        total_studies=1,
        included_studies=1,
        excluded_studies=0,
        citations=[
            CitationGroup(
                key="year:2020",
                nct_ids=["NCT00000001"],
            )
        ],
        warnings=[],
    )

    response = build_visualization_response(
        query=(
            "How have pembrolizumab trials changed since 2020?"
        ),
        plan=plan,
        result=result,
        studies=[study],
    )

    assert response.status == "completed"
    assert response.visualization.type == VisualizationType.TIME_SERIES

    assert response.visualization.data is not None
    assert len(response.visualization.data) == 1

    datum = response.visualization.data[0]

    assert datum.datum_id == "year:2020"
    assert datum.citation_ref == "year:2020"
    assert datum.model_extra == {
        "year": 2020,
        "trial_count": 1,
    }

    assert response.meta.records_matched == 1
    assert response.meta.records_used == 1
    assert response.meta.records_excluded == 0

    assert response.meta.filters_applied == {
        "drug_names": ["Pembrolizumab"],
        "start_year": 2020,
    }

    assert "year:2020" in response.citations

    citation_group = response.citations["year:2020"]

    assert citation_group.total_records == 1
    assert citation_group.records_returned == 1
    assert citation_group.truncated is False
    assert citation_group.records[0].nct_id == "NCT00000001"
    assert citation_group.records[0].excerpt == "2020-01-01"