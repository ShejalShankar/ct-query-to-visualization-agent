from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.visualizations import router as visualization_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.http_client = httpx.AsyncClient(
        base_url=settings.clinical_trials_base_url,
        timeout=httpx.Timeout(
            settings.clinical_trials_timeout_seconds
        ),
        headers={
            "Accept": "application/json",
            "User-Agent": (
                "clinical-trials-query-to-visualization-agent/0.1.0"
            ),
        },
    )

    try:
        yield
    finally:
        await app.state.http_client.aclose()


app = FastAPI(
    title="ClinicalTrials.gov Query-to-Visualization Agent",
    description=(
        "A backend service that converts natural-language clinical-trial "
        "questions into structured, traceable visualization specifications."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(visualization_router)


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    return {
        "name": "ClinicalTrials.gov Query-to-Visualization Agent",
        "documentation": "/docs",
        "health": "/health",
    }