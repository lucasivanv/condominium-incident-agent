"""Análise reproduzível de anomalias e risco a partir dos resultados do CI."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from xml.etree import ElementTree

StageStatus = Literal["success", "failure", "cancelled", "skipped", "unknown"]


@dataclass(frozen=True)
class TestSummary:
    """Resumo agregado de um relatório JUnit."""

    collected: int = 0
    failures: int = 0
    errors: int = 0
    skipped: int = 0
    duration_seconds: float = 0.0
    report_available: bool = False


@dataclass(frozen=True)
class Anomaly:
    """Sinal anômalo detectado e sua avaliação de risco."""

    code: str
    stage: str
    description: str
    probability: int
    impact: int

    @property
    def score(self) -> int:
        return self.probability * self.impact

    @property
    def level(self) -> str:
        return risk_level(self.score)


def risk_level(score: int) -> str:
    """Classifica uma pontuação de risco entre 1 e 25."""
    if score >= 17:
        return "CRITICAL"
    if score >= 10:
        return "HIGH"
    if score >= 5:
        return "MODERATE"
    return "LOW"


def normalize_status(value: str) -> StageStatus:
    """Normaliza resultados informados pelo GitHub Actions ou pela CLI."""
    normalized = value.strip().lower()
    if normalized in {"success", "failure", "cancelled", "skipped"}:
        return normalized  # type: ignore[return-value]
    return "unknown"


def parse_junit(path: Path) -> TestSummary:
    """Lê totais do elemento raiz de um relatório JUnit do pytest."""
    if not path.exists():
        return TestSummary()

    try:
        root = ElementTree.parse(path).getroot()
    except (ElementTree.ParseError, OSError):
        return TestSummary()

    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    if not suites and root.tag == "testsuites":
        suites = [root]

    def integer_total(attribute: str) -> int:
        return sum(int(suite.attrib.get(attribute, 0)) for suite in suites)

    def float_total(attribute: str) -> float:
        return sum(float(suite.attrib.get(attribute, 0)) for suite in suites)

    try:
        return TestSummary(
            collected=integer_total("tests"),
            failures=integer_total("failures"),
            errors=integer_total("errors"),
            skipped=integer_total("skipped"),
            duration_seconds=round(float_total("time"), 3),
            report_available=True,
        )
    except ValueError:
        return TestSummary()


def detect_anomalies(
    *,
    lint_status: str,
    test_status: str,
    build_status: str,
    tests: TestSummary,
    baseline_duration_seconds: float = 0.0,
) -> list[Anomaly]:
    """Detecta falhas e desvios relevantes sem depender de um modelo externo."""
    lint = normalize_status(lint_status)
    test = normalize_status(test_status)
    build = normalize_status(build_status)
    anomalies: list[Anomaly] = []

    if lint != "success":
        anomalies.append(
            Anomaly(
                code="LINT_STAGE_NOT_SUCCESSFUL",
                stage="lint",
                description=f"A etapa de lint terminou com status {lint}.",
                probability=5 if lint == "failure" else 4,
                impact=2,
            )
        )

    if test != "success":
        anomalies.append(
            Anomaly(
                code="TEST_STAGE_NOT_SUCCESSFUL",
                stage="tests",
                description=f"A etapa de testes terminou com status {test}.",
                probability=5 if test == "failure" else 4,
                impact=5,
            )
        )

    if build != "success":
        anomalies.append(
            Anomaly(
                code="BUILD_STAGE_NOT_SUCCESSFUL",
                stage="build",
                description=f"A etapa de build terminou com status {build}.",
                probability=5 if build == "failure" else 4,
                impact=4,
            )
        )

    if test == "success" and not tests.report_available:
        anomalies.append(
            Anomaly(
                code="MISSING_JUNIT_REPORT",
                stage="tests",
                description="A etapa passou, mas o relatório JUnit não foi produzido.",
                probability=4,
                impact=3,
            )
        )
    elif tests.report_available and tests.collected == 0:
        anomalies.append(
            Anomaly(
                code="NO_TESTS_COLLECTED",
                stage="tests",
                description="O relatório JUnit não contém testes coletados.",
                probability=5,
                impact=5,
            )
        )

    failed_tests = tests.failures + tests.errors
    if failed_tests:
        anomalies.append(
            Anomaly(
                code="TEST_FAILURES_REPORTED",
                stage="tests",
                description=f"O JUnit registrou {failed_tests} teste(s) com falha ou erro.",
                probability=5,
                impact=5,
            )
        )

    if (
        baseline_duration_seconds > 0
        and tests.report_available
        and tests.duration_seconds > baseline_duration_seconds * 1.5
    ):
        ratio = tests.duration_seconds / baseline_duration_seconds
        anomalies.append(
            Anomaly(
                code="TEST_DURATION_REGRESSION",
                stage="tests",
                description=(
                    "A duração dos testes atingiu "
                    f"{tests.duration_seconds:.3f}s ({ratio:.2f}x o baseline)."
                ),
                probability=3,
                impact=3,
            )
        )

    return anomalies


def build_report(
    *,
    lint_status: str,
    test_status: str,
    build_status: str,
    tests: TestSummary,
    baseline_duration_seconds: float = 0.0,
) -> dict:
    """Monta o relatório estruturado de qualidade e risco."""
    statuses = {
        "lint": normalize_status(lint_status),
        "tests": normalize_status(test_status),
        "build": normalize_status(build_status),
    }
    anomalies = detect_anomalies(
        lint_status=statuses["lint"],
        test_status=statuses["tests"],
        build_status=statuses["build"],
        tests=tests,
        baseline_duration_seconds=baseline_duration_seconds,
    )
    overall_score = max((anomaly.score for anomaly in anomalies), default=1)

    return {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "method": "probability_x_impact",
        "statuses": statuses,
        "tests": asdict(tests),
        "baseline_duration_seconds": baseline_duration_seconds,
        "anomalies": [
            {**asdict(anomaly), "score": anomaly.score, "level": anomaly.level}
            for anomaly in anomalies
        ],
        "overall_risk": {
            "score": overall_score,
            "level": risk_level(overall_score),
            "has_anomaly": bool(anomalies),
        },
    }


def render_markdown(report: dict) -> str:
    """Renderiza um resumo legível para artifact e GitHub Actions."""
    statuses = report["statuses"]
    tests = report["tests"]
    risk = report["overall_risk"]
    lines = [
        "# CI quality and risk report",
        "",
        f"- Lint: `{statuses['lint']}`",
        f"- Tests: `{statuses['tests']}`",
        f"- Build: `{statuses['build']}`",
        f"- Tests collected: `{tests['collected']}`",
        f"- Test duration: `{tests['duration_seconds']}s`",
        f"- Overall risk: `{risk['level']}` ({risk['score']}/25)",
        "",
        "## Anomalies",
        "",
    ]
    if not report["anomalies"]:
        lines.append("No anomaly detected.")
    else:
        for anomaly in report["anomalies"]:
            lines.append(
                f"- **{anomaly['code']}** — {anomaly['description']} "
                f"Risk: {anomaly['level']} ({anomaly['score']}/25)."
            )
    return "\n".join(lines) + "\n"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lint-status", required=True)
    parser.add_argument("--test-status", required=True)
    parser.add_argument("--build-status", required=True)
    parser.add_argument("--junit-path", type=Path, default=Path("artifacts/pytest.xml"))
    parser.add_argument("--baseline-duration-seconds", type=float, default=0.0)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    return parser


def main() -> None:
    """Executa a análise a partir dos resultados fornecidos pelo CI."""
    args = _build_parser().parse_args()
    tests = parse_junit(args.junit_path)
    report = build_report(
        lint_status=args.lint_status,
        test_status=args.test_status,
        build_status=args.build_status,
        tests=tests,
        baseline_duration_seconds=args.baseline_duration_seconds,
    )

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    markdown = render_markdown(report)
    args.markdown_output.write_text(markdown, encoding="utf-8")
    print(markdown)


if __name__ == "__main__":
    main()
