from collections import defaultdict
from collections.abc import Iterable

from app.analysis.models import (
    CitationGroup,
    GeographicPoint,
    GeographicRankingResult,
)
from app.clinical_trials.normalized_models import NormalizedStudy


def analyze_geographic_ranking(
    studies: Iterable[NormalizedStudy],
    *,
    limit: int | None = 10,
) -> GeographicRankingResult:
    """
    Rank countries by the number of studies conducted in each country.

    A multi-country study contributes once to every distinct country in which
    it operates. Duplicate country values within one study are counted once.
    """

    if limit is not None and limit <= 0:
        raise ValueError("limit must be greater than zero or None")

    study_list = list(studies)

    studies_by_country: dict[str, set[str]] = defaultdict(set)
    included_nct_ids: set[str] = set()
    excluded_count = 0

    for study in study_list:
        countries = _clean_countries(study.countries)

        if not countries:
            excluded_count += 1
            continue

        included_nct_ids.add(study.nct_id)

        for country in countries:
            studies_by_country[country].add(study.nct_id)

    ranked_countries = sorted(
        studies_by_country.items(),
        key=lambda item: (-len(item[1]), item[0]),
    )

    total_ranked_countries = len(ranked_countries)

    if limit is not None:
        ranked_countries = ranked_countries[:limit]

    points = [
        GeographicPoint(
            country=country,
            count=len(nct_ids),
        )
        for country, nct_ids in ranked_countries
    ]

    citations = [
        CitationGroup(
            key=country,
            nct_ids=sorted(nct_ids),
        )
        for country, nct_ids in ranked_countries
    ]

    warnings: list[str] = []

    if excluded_count:
        warnings.append(
            f"{excluded_count} studies were excluded because they had no "
            "usable country information."
        )

    country_assignments = sum(
        len(nct_ids)
        for nct_ids in studies_by_country.values()
    )

    if country_assignments > len(included_nct_ids):
        warnings.append(
            "Some studies contribute to multiple countries because they "
            "include sites in more than one country."
        )

    if limit is not None and total_ranked_countries > limit:
        warnings.append(
            f"Only the top {limit} of {total_ranked_countries} countries "
            "are included in the ranking."
        )

    if not points:
        warnings.insert(
            0,
            "No usable country information was found.",
        )

    return GeographicRankingResult(
        points=points,
        total_studies=len(study_list),
        included_studies=len(included_nct_ids),
        excluded_studies=excluded_count,
        country_assignments=country_assignments,
        citations=citations,
        warnings=warnings,
    )


def _clean_countries(countries: Iterable[str]) -> set[str]:
    return {
        country.strip()
        for country in countries
        if country and country.strip()
    }