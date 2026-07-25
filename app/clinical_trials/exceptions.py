class ClinicalTrialsError(Exception):
    """Base exception for ClinicalTrials.gov integration failures."""


class ClinicalTrialsTimeoutError(ClinicalTrialsError):
    """Raised when ClinicalTrials.gov does not respond before the timeout."""


class ClinicalTrialsAPIError(ClinicalTrialsError):
    """Raised when ClinicalTrials.gov returns an unsuccessful response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code


class ClinicalTrialsResponseError(ClinicalTrialsError):
    """Raised when the API returns an unexpected or malformed response."""