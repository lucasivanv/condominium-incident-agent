"""Testes do registro operacional e da auditoria por execução."""

from condominium_incident_agent.observability import (
    clear_observability,
    instrument_node,
    investigate_execution,
)


def _state(correlation_id: str) -> dict:
    return {
        "correlation_id": correlation_id,
        "category": None,
        "severity": None,
        "multiple_incidents_detected": False,
        "classification_error": None,
        "output_file": None,
        "escalated_file": None,
    }


def setup_function() -> None:
    clear_observability()


def test_records_structured_duration_and_independent_audit() -> None:
    state = _state("execution-a")

    def node(current: dict) -> dict:
        return {**current, "severity": "LOW"}

    instrument_node("example", node)(state)

    records = investigate_execution("execution-a")
    assert [record["event"] for record in records["logs"]] == ["started", "completed"]
    completed = records["logs"][1]
    assert completed["duration_ms"] >= 0
    assert completed["result"]["severity"] == "LOW"
    assert records["audit"][0]["event"] == "node_completed"
    assert records["audit"] is not records["logs"]


def test_investigation_isolated_by_correlation_id() -> None:
    instrument_node("example", lambda state: state)(_state("execution-a"))
    instrument_node("example", lambda state: state)(_state("execution-b"))

    result = investigate_execution("execution-a")
    assert result["logs"]
    assert result["audit"]
    assert all(record["correlation_id"] == "execution-a" for record in result["logs"])
    assert all(record["correlation_id"] == "execution-a" for record in result["audit"])


def test_records_do_not_contain_prompt_or_sensitive_input() -> None:
    secret_prompt = "prompt completo token=abc123 password=super-secret"
    state = _state("execution-safe")
    state["classification_error"] = secret_prompt

    instrument_node("example", lambda current: current)(state)
    records = investigate_execution("execution-safe")
    serialized = repr(records)
    assert secret_prompt not in serialized
    assert "abc123" not in serialized
    assert "super-secret" not in serialized


def test_records_controlled_node_errors() -> None:
    def failing_node(_state: dict) -> dict:
        raise RuntimeError("credential=do-not-log")

    try:
        instrument_node("failing", failing_node)(_state("execution-error"))
    except RuntimeError:
        pass

    records = investigate_execution("execution-error")
    assert records["logs"][1]["event"] == "failed"
    assert records["logs"][1]["error"] == "RuntimeError"
    assert records["audit"][0]["event"] == "node_failed"
    assert "do-not-log" not in repr(records)