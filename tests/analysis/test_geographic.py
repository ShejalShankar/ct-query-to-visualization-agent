from datetime import date

import pytest

from app.analysis.geographic import analyze_geographic_ranking
from app.clinical_trials.normalized_models import NormalizedStudy


def make_study(
    nct_id: str,
    *,
    countries: list[str] | None = None,
) -> NormalizedStudy:
    return NormalizedStudy(
        nct_id=nct_id,
        title=f"Study {nct_id}",
        overall_status="COMPLETED",
        start_date=date(2020, 1, 1),
        start_date_raw="2020-01-01",
        phases=[],
        conditions=[],
        interventions=[],
        lead_sponsor=None,
        countries=countries or [],
    )


def test_ranks_countries_by_study_count():
    studies = [
        make_study(
            "NCT00000001",
            countries=["United States", "Canada"],
        ),
        make_study(
            "NCT00000002",
            countries=["United States"],
        ),
        make_study(
            "NCT00000003",
            countries=["Austria"],
        ),
    ]

    result = analyze_geographic_ranking(studies)

    assert [
        (point.country, point.count)
        for point in result.points
    ] == [
        ("United States", 2),
        ("Austria", 1),
        ("Canada", 1),
    ]

    assert result.total_studies == 3
    assert result.included_studies == 3
    assert result.excluded_studies == 0
    assert result.country_assignments == 4


def test_multi_country_study_contributes_to_each_country():
    studies = [
        make_study(
            "NCT00000001",
            countries=[
                "United States",
                "Canada",
                "Austria",
            ],
        )
    ]

    result = analyze_geographic_ranking(studies)

    assert result.included_studies == 1
    assert result.country_assignments == 3
    assert any(
        "multiple countries" in warning
        for warning in result.warnings
    )


def test_deduplicates_country_within_one_study():
    studies = [
        make_study(
            "NCT00000001",
            countries=[
                "United States",
                "United States",
                " United States ",
            ],
        )
    ]

    result = analyze_geographic_ranking(studies)

    assert len(result.points) == 1
    assert result.points[0].country == "United States"
    assert result.points[0].count == 1
    assert result.country_assignments == 1


def test_excludes_studies_without_country_information():
    studies = [
        make_study(
            "NCT00000001",
            countries=["Canada"],
        ),
        make_study(
            "NCT00000002",
            countries=[],
        ),
    ]

    result = analyze_geographic_ranking(studies)

    assert result.included_studies == 1
    assert result.excluded_studies == 1
    assert any(
        "excluded" in warning
        for warning in result.warnings
    )


def test_applies_country_limit():
    studies = [
        make_study(
            "NCT00000001",
            countries=["Canada"],
        ),
        make_study(
            "NCT00000002",
            countries=["Austria"],
        ),
        make_study(
            "NCT00000003",
            countries=["United States"],
        ),
    ]

    result = analyze_geographic_ranking(
        studies,
        limit=2,
    )

    assert len(result.points) == 2
    assert any(
        "top 2" in warning
        for warning in result.warnings
    )


def test_generates_country_level_citations():
    studies = [
        make_study(
            "NCT00000002",
            countries=["United States"],
        ),
        make_study(
            "NCT00000001",
            countries=["United States"],
        ),
    ]

    result = analyze_geographic_ranking(studies)

    assert result.citations[0].key == "United States"
    assert result.citations[0].nct_ids == [
        "NCT00000001",
        "NCT00000002",
    ]


def test_returns_warning_when_no_country_values_exist():
    studies = [
        make_study(
            "NCT00000001",
            countries=[],
        ),
        make_study(
            "NCT00000002",
            countries=[],
        ),
    ]

    result = analyze_geographic_ranking(studies)

    assert result.points == []
    assert result.included_studies == 0
    assert result.excluded_studies == 2
    assert result.country_assignments == 0
    assert result.warnings


def test_rejects_non_positive_limit():
    with pytest.raises(
        ValueError,
        match="limit must be greater than zero",
    ):
        analyze_geographic_ranking(
            [],
            limit=0,
        )
