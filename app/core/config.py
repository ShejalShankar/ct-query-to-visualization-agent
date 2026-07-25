import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    clinical_trials_base_url: str = os.getenv(
        "CLINICAL_TRIALS_BASE_URL",
        "https://clinicaltrials.gov/api/v2",
    )

    clinical_trials_timeout_seconds: float = float(
        os.getenv(
            "CLINICAL_TRIALS_TIMEOUT_SECONDS",
            "20",
        )
    )

    clinical_trials_page_size: int = int(
        os.getenv(
            "CLINICAL_TRIALS_PAGE_SIZE",
            "100",
        )
    )

    openai_api_key: str = os.getenv(
        "OPENAI_API_KEY",
        "",
    )

    openai_model: str = os.getenv(
        "OPENAI_MODEL",
        "gpt-5-mini",
    )


settings = Settings()