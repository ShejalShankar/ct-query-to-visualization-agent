from typing import Annotated

from fastapi import Depends

from app.clinical_trials.client import ClinicalTrialsClient
from app.clinical_trials.dependencies import (
    get_clinical_trials_client,
)
from app.orchestration.orchestrator import (
    VisualizationOrchestrator,
)
from app.planner.dependencies import get_planner
from app.planner.llm_planner import LLMPlanner


def get_visualization_orchestrator(
    planner: Annotated[
        LLMPlanner,
        Depends(get_planner),
    ],
    clinical_trials_client: Annotated[
        ClinicalTrialsClient,
        Depends(get_clinical_trials_client),
    ],
) -> VisualizationOrchestrator:
    return VisualizationOrchestrator(
        planner=planner,
        clinical_trials_client=clinical_trials_client,
    )