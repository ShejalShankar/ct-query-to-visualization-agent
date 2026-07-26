from datetime import UTC, datetime
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.main import app
from app.orchestration.dependencies import (
    get_visualization_orchestrator,
)
from app.schemas.analysis_plan import (
    AnalysisFilters,
    AnalysisIntent,
    AnalysisPlan,
    GroupByDimension,
    VisualizationType,
)
from app.schemas.response import (
    ChartDatum,
    ResponseMetadata,
    VisualizationChannel,
    VisualizationResponse,
    VisualizationSpecification,
)


def build_response() -> VisualizationResponse:
    plan = AnalysisPlan(
        intent=AnalysisIntent.TIME_TREND,
        group_by=GroupByDimension.START_YEAR,
        filters=AnalysisFilters(
            drug_names=["Pembrolizumab"],
            start_year=2020,
        ),
        visualization_type=VisualizationType.TIME_SERIES,
        confidence=0.96,
        reasoning_summary=(
            "The query asks how trial volume changed over time."
        ),
    )

    return VisualizationResponse(
        visualization=VisualizationSpecification(
            type=VisualizationType.TIME_SERIES,
            title="Pembrolizumab Trials Started by Year",
            description=(
                "Number of matching studies grouped by study start year."
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
            data=[
                ChartDatum(
                    datum_id="year:2020",
                    citation_ref=None,
                    year=2020,
                    trial_count=1,
                )
            ],
        ),
        meta=ResponseMetadata(
            generated_at=datetime.now(UTC),
            query=(
                "How have pembrolizumab trials changed since 2020?"
            ),
            analysis_plan=plan,
            filters_applied={
                "drug_names": ["Pembrolizumab"],
                "start_year": 2020,
            },
            records_matched=1,
            records_used=1,
            records_excluded=0,
            assumptions=[],
            warnings=[],
            partial_results=False,
        ),
        citations={},
    )


def test_create_visualization_endpoint() -> None:
    mock_orchestrator = AsyncMock()
    mock_orchestrator.run.return_value = build_response()

    app.dependency_overrides[
        get_visualization_orchestrator
    ] = lambda: mock_orchestrator

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/visualizations",
                json={
                    "query": (
                        "How have pembrolizumab trials changed "
                        "since 2020?"
                    ),
                    "drug_names": ["Pembrolizumab"],
                    "start_year": 2020,
                    "max_studies": 100,
                },
            )

        assert response.status_code == 200

        payload = response.json()

        assert payload["status"] == "completed"
        assert payload["visualization"]["type"] == "time_series"
        assert payload["visualization"]["data"][0] == {
            "datum_id": "year:2020",
            "citation_ref": None,
            "year": 2020,
            "trial_count": 1,
        }

        mock_orchestrator.run.assert_awaited_once()

        received_request = mock_orchestrator.run.await_args.args[0]

        assert received_request.query == (
            "How have pembrolizumab trials changed since 2020?"
        )
        assert received_request.max_studies == 100

    finally:
        app.dependency_overrides.clear()


def test_create_visualization_rejects_invalid_request() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/visualizations",
            json={
                "query": "x",
            },
        )

    assert response.status_code == 422