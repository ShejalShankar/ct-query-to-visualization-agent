from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.clinical_trials.models import StudySearchResult
from app.orchestration.orchestrator import (
    VisualizationOrchestrator,
)
from app.schemas.analysis_plan import (
    AnalysisFilters,
    AnalysisIntent,
    AnalysisPlan,
    GroupByDimension,
    VisualizationType,
)
from app.schemas.request import VisualizationRequest


def build_raw_study(
    *,
    nct_id: str = "NCT00000001",
    start_date: str = "2020-01-01",
) -> dict:
    return {
        "protocolSection": {
            "identificationModule": {
                "nctId": nct_id,
                "briefTitle": "Example Clinical Study",
            },
            "statusModule": {
                "overallStatus": "COMPLETED",
                "startDateStruct": {
                    "date": start_date,
                },
            },
            "designModule": {
                "phases": ["PHASE2"],
            },
            "conditionsModule": {
                "conditions": ["Melanoma"],
            },
            "armsInterventionsModule": {
                "interventions": [
                    {
                        "name": "Pembrolizumab",
                        "type": "DRUG",
                    }
                ],
            },
            "sponsorCollaboratorsModule": {
                "leadSponsor": {
                    "name": "Example Sponsor",
                    "class": "INDUSTRY",
                },
            },
            "contactsLocationsModule": {
                "locations": [
                    {
                        "country": "United States",
                    }
                ],
            },
        }
    }


def build_time_trend_plan() -> AnalysisPlan:
    return AnalysisPlan(
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


@pytest.mark.asyncio
async def test_runs_complete_visualization_pipeline() -> None:
    planner = SimpleNamespace(
        create_plan=AsyncMock(
            return_value=build_time_trend_plan()
        )
    )

    clinical_trials_client = SimpleNamespace(
        search_studies=AsyncMock(
            return_value=StudySearchResult(
                studies=[build_raw_study()],
                total_count=1,
                retrieved_count=1,
                pages_retrieved=1,
                partial_results=False,
            )
        )
    )

    orchestrator = VisualizationOrchestrator(
        planner=planner,
        clinical_trials_client=clinical_trials_client,
    )

    request = VisualizationRequest(
        query=(
            "How have pembrolizumab trials changed since 2020?"
        ),
        max_studies=100,
    )

    response = await orchestrator.run(request)

    assert response.status == "completed"
    assert response.visualization.type == (
        VisualizationType.TIME_SERIES
    )

    assert response.visualization.data is not None
    assert len(response.visualization.data) == 1

    datum = response.visualization.data[0]

    assert datum.model_extra == {
        "year": 2020,
        "trial_count": 1,
    }

    planner.create_plan.assert_awaited_once_with(
        request.query
    )

    clinical_trials_client.search_studies.assert_awaited_once_with(
        query_term='"Pembrolizumab"',
        max_studies=100,
    )


@pytest.mark.asyncio
async def test_explicit_request_fields_override_planner_filters() -> None:
    planned = build_time_trend_plan()

    planner = SimpleNamespace(
        create_plan=AsyncMock(
            return_value=planned
        )
    )

    clinical_trials_client = SimpleNamespace(
        search_studies=AsyncMock(
            return_value=StudySearchResult(
                studies=[
                    build_raw_study(
                        start_date="2022-01-01",
                    )
                ],
                total_count=1,
                retrieved_count=1,
                pages_retrieved=1,
                partial_results=False,
            )
        )
    )

    orchestrator = VisualizationOrchestrator(
        planner=planner,
        clinical_trials_client=clinical_trials_client,
    )

    response = await orchestrator.run(
        VisualizationRequest(
            query="Show the trend for this drug.",
            drug_names=["Nivolumab"],
            start_year=2022,
        )
    )

    assert response.meta.analysis_plan.filters.drug_names == [
        "Nivolumab"
    ]
    assert response.meta.analysis_plan.filters.start_year == 2022

    clinical_trials_client.search_studies.assert_awaited_once_with(
        query_term='"Nivolumab"',
        max_studies=2000,
    )


@pytest.mark.asyncio
async def test_removes_citations_when_not_requested() -> None:
    planner = SimpleNamespace(
        create_plan=AsyncMock(
            return_value=build_time_trend_plan()
        )
    )

    clinical_trials_client = SimpleNamespace(
        search_studies=AsyncMock(
            return_value=StudySearchResult(
                studies=[build_raw_study()],
                total_count=1,
                retrieved_count=1,
                pages_retrieved=1,
                partial_results=False,
            )
        )
    )

    orchestrator = VisualizationOrchestrator(
        planner=planner,
        clinical_trials_client=clinical_trials_client,
    )

    response = await orchestrator.run(
        VisualizationRequest(
            query=(
                "How have pembrolizumab trials changed since 2020?"
            ),
            include_citations=False,
        )
    )

    assert response.citations == {}

    assert response.visualization.data is not None
    assert response.visualization.data[0].citation_ref is None