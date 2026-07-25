import httpx
from fastapi import Request

from app.clinical_trials.client import ClinicalTrialsClient


def get_clinical_trials_client(
    request: Request,
) -> ClinicalTrialsClient:
    http_client: httpx.AsyncClient = request.app.state.http_client

    return ClinicalTrialsClient(
        http_client=http_client,
    )