from fastapi import APIRouter, Depends, Query
from app.schemas.analysis_plan import AnalysisPlan
from app.schemas.request import VisualizationRequest
from app.schemas.response import VisualizationResponse
from typing import Annotated
from app.clinical_trials.client import ClinicalTrialsClient
from app.clinical_trials.dependencies import get_clinical_trials_client
from app.clinical_trials.normalizer import normalize_studies

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


@router.get("/clinical-trials/normalized-search")
async def search_normalized_clinical_trials(
    client: Annotated[
        ClinicalTrialsClient,
        Depends(get_clinical_trials_client),
    ],
    query_term: Annotated[
        str,
        Query(min_length=2, max_length=300),
    ],
    max_studies: Annotated[
        int,
        Query(ge=1, le=100),
    ] = 10,
) -> dict[str, object]:
    search_result = await client.search_studies(
        query_term=query_term,
        max_studies=max_studies,
    )

    normalization_result = normalize_studies(
        search_result.studies
    )

    return {
        "retrieval": {
            "total_count": search_result.total_count,
            "retrieved_count": search_result.retrieved_count,
            "pages_retrieved": search_result.pages_retrieved,
            "partial_results": search_result.partial_results,
        },
        "normalization": normalization_result.model_dump(
            mode="json"
        ),
    }