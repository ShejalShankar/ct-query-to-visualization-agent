from fastapi import APIRouter

from app.schemas.request import VisualizationRequest

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