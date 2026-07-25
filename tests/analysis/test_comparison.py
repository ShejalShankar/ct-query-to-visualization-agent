from datetime import date

import pytest

from app.analysis.comparison import (
    analyze_intervention_comparison,
)
from app.clinical_trials.normalized_models import (
    NormalizedIntervention,
    NormalizedInterventionType,
    NormalizedStudy,
)


def make_study(
    nct_id: str,
    *,
    start_date: date | None,
    intervention_names: list[str],
) -> NormalizedStudy:
    return NormalizedStudy(
        nct_id=nct_id,
        title=f"Study {nct_id}",
        overall_status="COMPLETED",
        start_date=start_date,
        start_date_raw=(
            start_date.isoformat()
            if start_date is not None
            else None
        ),
        phases=[],
        conditions=[],
        interventions=[
            NormalizedIntervention(
                name=name,
                intervention_type=NormalizedInterventionType.DRUG,
            )
            for name in intervention_names
        ],
        lead_sponsor=None,
        countries=[],
    )


def test_compares_interventions_by_year():
    studies = [
        make_study(
            "NCT00000001",
            start_date=date(2020, 1, 1),
            intervention_names=["Pembrolizumab"],
        ),
        make_study(
            "NCT00000002",
            start_date=date(2020, 2, 1),
            intervention_names=["Nivolumab"],
        ),
        make_study(
            "NCT00000003",
            start_date=date(2021, 1, 1),
            intervention_names=["Pembrolizumab"],
        ),
    ]

    result = analyze_intervention_comparison(
        studies,
        intervention_names=[
            "Pembrolizumab",
            "Nivolumab",
        ],
    )

    assert result.series[0].label == "Pembrolizumab"
    assert [
        (point.year, point.count)
        for point in result.series[0].points
    ] == [
        (2020, 1),
        (2021, 1),
    ]

    assert result.series[1].label == "Nivolumab"
    assert [
        (point.year, point.count)
        for point in result.series[1].points
    ] == [
        (2020, 1),
        (2021, 0),
    ]


def test_matching_is_case_insensitive_and_whitespace_normalized():
    studies = [
        make_study(
            "NCT00000001",
            start_date=date(2020, 1, 1),
            intervention_names=["  PEMBROLIZUMAB  "],
        ),
        make_study(
            "NCT00000002",
            start_date=date(2020, 1, 1),
            intervention_names=["Nivolumab"],
        ),
    ]

    result = analyze_intervention_comparison(
        studies,
        intervention_names=[
            "pembrolizumab",
            "nivolumab",
        ],
    )

    assert result.included_studies == 2
    assert result.excluded_studies == 0


def test_study_can_contribute_to_multiple_groups():
    studies = [
        make_study(
            "NCT00000001",
            start_date=date(2020, 1, 1),
            intervention_names=[
                "Pembrolizumab",
                "Nivolumab",
            ],
        )
    ]

    result = analyze_intervention_comparison(
        studies,
        intervention_names=[
            "Pembrolizumab",
            "Nivolumab",
        ],
    )

    assert result.included_studies == 1
    assert result.overlapping_studies == 1

    assert result.series[0].points[0].count == 1
    assert result.series[1].points[0].count == 1

    assert any(
        "multiple series" in warning
        for warning in result.warnings
    )


def test_excludes_non_matching_studies():
    studies = [
        make_study(
            "NCT00000001",
            start_date=date(2020, 1, 1),
            intervention_names=["Pembrolizumab"],
        ),
        make_study(
            "NCT00000002",
            start_date=date(2020, 1, 1),
            intervention_names=["Ipilimumab"],
        ),
    ]

    result = analyze_intervention_comparison(
        studies,
        intervention_names=[
            "Pembrolizumab",
            "Nivolumab",
        ],
    )

    assert result.included_studies == 1
    assert result.excluded_studies == 1


def test_excludes_study_without_start_date():
    studies = [
        make_study(
            "NCT00000001",
            start_date=None,
            intervention_names=["Pembrolizumab"],
        ),
        make_study(
            "NCT00000002",
            start_date=date(2020, 1, 1),
            intervention_names=["Nivolumab"],
        ),
    ]

    result = analyze_intervention_comparison(
        studies,
        intervention_names=[
            "Pembrolizumab",
            "Nivolumab",
        ],
    )

    assert result.included_studies == 1
    assert result.excluded_studies == 1


def test_applies_inclusive_year_range():
    studies = [
        make_study(
            "NCT00000001",
            start_date=date(2019, 1, 1),
            intervention_names=["Pembrolizumab"],
        ),
        make_study(
            "NCT00000002",
            start_date=date(2020, 1, 1),
            intervention_names=["Pembrolizumab"],
        ),
        make_study(
            "NCT00000003",
            start_date=date(2021, 1, 1),
            intervention_names=["Nivolumab"],
        ),
    ]

    result = analyze_intervention_comparison(
        studies,
        intervention_names=[
            "Pembrolizumab",
            "Nivolumab",
        ],
        start_year=2020,
        end_year=2021,
    )

    assert [
        point.year
        for point in result.series[0].points
    ] == [2020, 2021]

    assert result.series[0].points[0].count == 1
    assert result.series[1].points[1].count == 1


def test_generates_group_and_year_citations():
    studies = [
        make_study(
            "NCT00000002",
            start_date=date(2020, 1, 1),
            intervention_names=["Pembrolizumab"],
        ),
        make_study(
            "NCT00000001",
            start_date=date(2020, 1, 1),
            intervention_names=["Pembrolizumab"],
        ),
    ]

    result = analyze_intervention_comparison(
        studies,
        intervention_names=[
            "Pembrolizumab",
            "Nivolumab",
        ],
    )

    citation = next(
        item
        for item in result.citations
        if item.key == "Pembrolizumab:2020"
    )

    assert citation.nct_ids == [
        "NCT00000001",
        "NCT00000002",
    ]


def test_warns_when_group_has_no_exact_matches():
    studies = [
        make_study(
            "NCT00000001",
            start_date=date(2020, 1, 1),
            intervention_names=["Pembrolizumab"],
        )
    ]

    result = analyze_intervention_comparison(
        studies,
        intervention_names=[
            "Pembrolizumab",
            "Keytruda",
        ],
    )

    assert any(
        "Keytruda" in warning
        for warning in result.warnings
    )


def test_requires_two_distinct_intervention_names():
    with pytest.raises(
        ValueError,
        match="At least two distinct",
    ):
        analyze_intervention_comparison(
            [],
            intervention_names=[
                "Pembrolizumab",
                " pembrolizumab ",
            ],
        )