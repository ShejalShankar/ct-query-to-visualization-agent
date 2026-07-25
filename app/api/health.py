from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "clinical-trials-query-to-visualization-agent",
        "version": "0.1.0",
    }