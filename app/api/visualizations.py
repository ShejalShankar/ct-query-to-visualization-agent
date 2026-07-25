from fastapi import APIRouter, Depends, Query
from app.schemas.analysis_plan import AnalysisPlan
from app.schemas.request import VisualizationRequest
from app.schemas.response import VisualizationResponse
from typing import Annotated
from app.clinical_trials.client import ClinicalTrialsClient
from app.clinical_trials.dependencies import get_clinical_trials_client

router = APIRouter(
    prefix="/api/v1",
    tags=["visualizations"],
)


@router.post("/visualizations/validate")
async def validate_visualization_request(
    request: VisualizationRequest,
) -> dict[str, object]:
    return {
        "status": "valid",
        "normalized_request": request.model_dump(mode="json"),
    }


@router.post("/analysis-plans/validate")
async def validate_analysis_plan(
    plan: AnalysisPlan,
) -> dict[str, object]:
    return {
        "status": "valid",
        "analysis_plan": plan.model_dump(mode="json"),
    }

@router.post("/responses/validate")
async def validate_visualization_response(
    response: VisualizationResponse,
) -> dict[str, object]:
    return {
        "status": "valid",
        "response": response.model_dump(mode="json"),
    }

@router.get("/clinical-trials/search")
async def search_clinical_trials(
    client: Annotated[
        ClinicalTrialsClient,
        Depends(get_clinical_trials_client),
    ],
    query_term: Annotated[
        str,
        Query(
            min_length=2,
            max_length=300,
            description="ClinicalTrials.gov full-text search query.",
        ),
    ],
    max_studies: Annotated[
        int,
        Query(ge=1, le=1000),
    ] = 10,
) -> dict[str, object]:
    result = await client.search_studies(
        query_term=query_term,
        max_studies=max_studies,
    )

    return result.model_dump(mode="json")