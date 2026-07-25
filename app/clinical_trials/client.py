from collections.abc import Sequence
from typing import Any

import httpx

from app.clinical_trials.exceptions import (
    ClinicalTrialsAPIError,
    ClinicalTrialsResponseError,
    ClinicalTrialsTimeoutError,
)
from app.clinical_trials.models import StudySearchResult
from app.core.config import Settings, settings


DEFAULT_STUDY_FIELDS: tuple[str, ...] = (
    "NCTId",
    "BriefTitle",
    "OverallStatus",
    "StartDate",
    "Phase",
    "Condition",
    "InterventionName",
    "InterventionType",
    "LeadSponsorName",
    "LeadSponsorClass",
    "LocationCountry",
)


class ClinicalTrialsClient:
    """
    Async adapter for the ClinicalTrials.gov v2 studies API.

    This class owns API-specific concerns such as pagination, query parameter
    names, timeouts, and upstream response validation.
    """

    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient,
        app_settings: Settings = settings,
    ) -> None:
        self._http_client = http_client
        self._settings = app_settings

    async def search_studies(
        self,
        *,
        query_term: str,
        max_studies: int,
        fields: Sequence[str] = DEFAULT_STUDY_FIELDS,
    ) -> StudySearchResult:
        cleaned_query = query_term.strip()

        if not cleaned_query:
            raise ValueError("query_term must not be empty")

        if max_studies < 1:
            raise ValueError("max_studies must be at least 1")

        studies: list[dict[str, Any]] = []
        page_token: str | None = None
        pages_retrieved = 0
        total_count: int | None = None

        while len(studies) < max_studies:
            remaining = max_studies - len(studies)

            page_size = min(
                self._settings.clinical_trials_page_size,
                remaining,
                1000,
            )

            payload = await self._fetch_page(
                query_term=cleaned_query,
                page_size=page_size,
                page_token=page_token,
                fields=fields,
            )

            pages_retrieved += 1

            page_studies = payload.get("studies")
            if not isinstance(page_studies, list):
                raise ClinicalTrialsResponseError(
                    "ClinicalTrials.gov response did not contain a valid "
                    "'studies' array"
                )

            for study in page_studies:
                if not isinstance(study, dict):
                    raise ClinicalTrialsResponseError(
                        "ClinicalTrials.gov returned a non-object study record"
                    )

                studies.append(study)

                if len(studies) >= max_studies:
                    break

            if total_count is None:
                raw_total_count = payload.get("totalCount")

                if raw_total_count is not None:
                    if not isinstance(raw_total_count, int):
                        raise ClinicalTrialsResponseError(
                            "ClinicalTrials.gov returned an invalid totalCount"
                        )

                    total_count = raw_total_count

            raw_next_page_token = payload.get("nextPageToken")

            if raw_next_page_token is not None and not isinstance(
                raw_next_page_token,
                str,
            ):
                raise ClinicalTrialsResponseError(
                    "ClinicalTrials.gov returned an invalid nextPageToken"
                )

            page_token = raw_next_page_token

            if not page_token:
                break

            if not page_studies:
                raise ClinicalTrialsResponseError(
                    "ClinicalTrials.gov returned an empty page with a "
                    "nextPageToken"
                )

        partial_results = bool(
            page_token
            and len(studies) >= max_studies
        )

        return StudySearchResult(
            studies=studies,
            total_count=total_count,
            retrieved_count=len(studies),
            pages_retrieved=pages_retrieved,
            partial_results=partial_results,
        )

    async def _fetch_page(
        self,
        *,
        query_term: str,
        page_size: int,
        page_token: str | None,
        fields: Sequence[str],
    ) -> dict[str, Any]:
        params: dict[str, str | int | bool] = {
            "query.term": query_term,
            "pageSize": page_size,
            "format": "json",
            "countTotal": True,
        }

        if fields:
            params["fields"] = ",".join(fields)

        if page_token:
            params["pageToken"] = page_token

        try:
            response = await self._http_client.get(
                "/studies",
                params=params,
            )

            response.raise_for_status()

        except httpx.TimeoutException as exc:
            raise ClinicalTrialsTimeoutError(
                "ClinicalTrials.gov request timed out"
            ) from exc

        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code

            raise ClinicalTrialsAPIError(
                (
                    "ClinicalTrials.gov returned an unsuccessful response "
                    f"with status code {status_code}"
                ),
                status_code=status_code,
            ) from exc

        except httpx.RequestError as exc:
            raise ClinicalTrialsAPIError(
                "Unable to connect to ClinicalTrials.gov"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise ClinicalTrialsResponseError(
                "ClinicalTrials.gov returned invalid JSON"
            ) from exc

        if not isinstance(payload, dict):
            raise ClinicalTrialsResponseError(
                "ClinicalTrials.gov returned an unexpected response shape"
            )

        return payload