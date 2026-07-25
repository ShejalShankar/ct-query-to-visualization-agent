from datetime import date

from app.analysis.time_trend import analyze_time_trend
from app.clinical_trials.normalized_models import NormalizedStudy


def make_study(
    nct_id: str,
    start_date: date | None,
) -> NormalizedStudy:
    return NormalizedStudy(
        nct_id=nct_id,
        title=f"Study {nct_id}",
        overall_status="COMPLETED",
        start_date=start_date,
        start_date_raw=start_date.isoformat() if start_date else None,
        phases=[],
        conditions=[],
        interventions=[],
        lead_sponsor=None,
        countries=[],
    )


def test_groups_studies_by_start_year():
    studies = [
        make_study("NCT00000001", date(2020, 1, 1)),
        make_study("NCT00000002", date(2020, 8, 12)),
        make_study("NCT00000003", date(2021, 3, 4)),
    ]

    result = analyze_time_trend(studies)

    assert [(point.year, point.count) for point in result.points] == [
        (2020, 2),
        (2021, 1),
    ]

    assert result.total_studies == 3
    assert result.included_studies == 3
    assert result.excluded_studies == 0


def test_fills_missing_years_with_zero():
    studies = [
        make_study("NCT00000001", date(2019, 1, 1)),
        make_study("NCT00000002", date(2021, 1, 1)),
    ]

    result = analyze_time_trend(studies)

    assert [(point.year, point.count) for point in result.points] == [
        (2019, 1),
        (2020, 0),
        (2021, 1),
    ]


def test_applies_inclusive_year_range():
    studies = [
        make_study("NCT00000001", date(2018, 1, 1)),
        make_study("NCT00000002", date(2019, 1, 1)),
        make_study("NCT00000003", date(2020, 1, 1)),
        make_study("NCT00000004", date(2021, 1, 1)),
    ]

    result = analyze_time_trend(
        studies,
        start_year=2019,
        end_year=2020,
    )

    assert [(point.year, point.count) for point in result.points] == [
        (2019, 1),
        (2020, 1),
    ]


def test_excludes_missing_start_dates_and_adds_warning():
    studies = [
        make_study("NCT00000001", date(2020, 1, 1)),
        make_study("NCT00000002", None),
    ]

    result = analyze_time_trend(studies)

    assert result.included_studies == 1
    assert result.excluded_studies == 1
    assert len(result.warnings) == 1


def test_generates_citations_for_each_year():
    studies = [
        make_study("NCT00000002", date(2020, 1, 1)),
        make_study("NCT00000001", date(2020, 1, 1)),
        make_study("NCT00000003", date(2021, 1, 1)),
    ]

    result = analyze_time_trend(studies)

    assert result.citations[0].key == "2020"
    assert result.citations[0].nct_ids == [
        "NCT00000001",
        "NCT00000002",
    ]

    assert result.citations[1].key == "2021"
    assert result.citations[1].nct_ids == ["NCT00000003"]


def test_returns_warning_when_no_usable_studies_exist():
    studies = [
        make_study("NCT00000001", None),
        make_study("NCT00000002", None),
    ]

    result = analyze_time_trend(studies)

    assert result.points == []
    assert result.included_studies == 0
    assert result.excluded_studies == 2
    assert result.warnings