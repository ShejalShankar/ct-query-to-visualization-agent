from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.visualizations import router as visualization_router

app = FastAPI(
    title="ClinicalTrials.gov Query-to-Visualization Agent",
    description=(
        "A backend service that converts natural-language clinical-trial "
        "questions into structured, traceable visualization specifications."
    ),
    version="0.1.0",
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