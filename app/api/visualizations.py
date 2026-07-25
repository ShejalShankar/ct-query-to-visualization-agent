from fastapi import APIRouter
from app.schemas.analysis_plan import AnalysisPlan
from app.schemas.request import VisualizationRequest
from app.schemas.response import VisualizationResponse

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