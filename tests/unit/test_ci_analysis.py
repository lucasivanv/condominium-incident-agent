"""Testes da detecção de anomalias e estimativa de risco do CI."""

from pathlib import Path

from condominium_incident_agent.ci_analysis import (
    TestSummary as CiTestSummary,
)
from condominium_incident_agent.ci_analysis import (
    build_report,
    detect_anomalies,
    parse_junit,
    render_markdown,
    risk_level,
)


def _summary(**overrides) -> CiTestSummary:
    values = {
        "collected": 203,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "duration_seconds": 4.0,
        "report_available": True,
    }
    values.update(overrides)
    return CiTestSummary(**values)


def test_successful_pipeline_has_low_risk_and_no_anomaly():
    report = build_report(
        lint_status="success",
        test_status="success",
        build_status="success",
        tests=_summary(),
        baseline_duration_seconds=5,
    )

    assert report["anomalies"] == []
    assert report["overall_risk"] == {
        "score": 1,
        "level": "LOW",
        "has_anomaly": False,
    }


def test_failed_tests_are_a_critical_anomaly():
    report = build_report(
        lint_status="success",
        test_status="failure",
        build_status="success",
        tests=_summary(failures=1),
    )

    codes = {anomaly["code"] for anomaly in report["anomalies"]}
    assert codes == {"TEST_STAGE_NOT_SUCCESSFUL", "TEST_FAILURES_REPORTED"}
    assert report["overall_risk"]["score"] == 25
    assert report["overall_risk"]["level"] == "CRITICAL"


def test_missing_junit_after_success_is_detected():
    anomalies = detect_anomalies(
        lint_status="success",
        test_status="success",
        build_status="success",
        tests=CiTestSummary(),
    )

    assert [anomaly.code for anomaly in anomalies] == ["MISSING_JUNIT_REPORT"]


def test_zero_collected_tests_are_critical():
    anomalies = detect_anomalies(
        lint_status="success",
        test_status="success",
        build_status="success",
        tests=_summary(collected=0),
    )

    anomaly = anomalies[0]
    assert anomaly.code == "NO_TESTS_COLLECTED"
    assert anomaly.score == 25


def test_duration_above_one_and_a_half_times_baseline_is_detected():
    anomalies = detect_anomalies(
        lint_status="success",
        test_status="success",
        build_status="success",
        tests=_summary(duration_seconds=15.1),
        baseline_duration_seconds=10,
    )

    assert [anomaly.code for anomaly in anomalies] == ["TEST_DURATION_REGRESSION"]
    assert anomalies[0].score == 9
    assert anomalies[0].level == "MODERATE"


def test_duration_equal_to_threshold_is_not_anomaly():
    anomalies = detect_anomalies(
        lint_status="success",
        test_status="success",
        build_status="success",
        tests=_summary(duration_seconds=15),
        baseline_duration_seconds=10,
    )

    assert anomalies == []


def test_parse_junit_reads_pytest_aggregate(tmp_path: Path):
    report_path = tmp_path / "pytest.xml"
    report_path.write_text(
        '<testsuites tests="7" failures="1" errors="2" skipped="1" time="3.25" />',
        encoding="utf-8",
    )

    summary = parse_junit(report_path)

    assert summary == CiTestSummary(
        collected=7,
        failures=1,
        errors=2,
        skipped=1,
        duration_seconds=3.25,
        report_available=True,
    )


def test_invalid_junit_is_treated_as_unavailable(tmp_path: Path):
    report_path = tmp_path / "pytest.xml"
    report_path.write_text("not XML", encoding="utf-8")

    assert parse_junit(report_path) == CiTestSummary()


def test_junit_with_invalid_totals_is_treated_as_unavailable(tmp_path: Path):
    report_path = tmp_path / "pytest.xml"
    report_path.write_text(
        '<testsuites tests="not-a-number" failures="0" errors="0" time="1" />',
        encoding="utf-8",
    )

    assert parse_junit(report_path) == CiTestSummary()


def test_markdown_contains_status_risk_and_anomaly():
    report = build_report(
        lint_status="failure",
        test_status="success",
        build_status="success",
        tests=_summary(),
    )

    markdown = render_markdown(report)

    assert "Lint: `failure`" in markdown
    assert "Overall risk: `HIGH` (10/25)" in markdown
    assert "LINT_STAGE_NOT_SUCCESSFUL" in markdown


def test_risk_level_boundaries():
    assert risk_level(1) == "LOW"
    assert risk_level(5) == "MODERATE"
    assert risk_level(10) == "HIGH"
    assert risk_level(17) == "CRITICAL"
