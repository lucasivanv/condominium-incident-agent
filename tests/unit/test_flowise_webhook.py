"""Testes da integração HTTP externa com o Flowise."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

from condominium_incident_agent.enums import Category, Severity
from condominium_incident_agent.nodes.send_to_flowise import send_to_flowise
from condominium_incident_agent.tools.flowise_webhook import build_flowise_payload


def _state(**overrides) -> dict:
    state = {
        "occurrence_id": "occ-123",
        "correlation_id": "corr-456",
        "reported_at": "2026-08-23T12:00:00Z",
        "category": Category.NOISE,
        "severity": Severity.LOW,
        "summary": "Barulho excessivo.",
        "involved_people": ["Joao"],
        "apartment": "302",
        "building": "A",
        "output_file": "reports/occ-123.json",
        "classification_error": None,
    }
    state.update(overrides)
    return state


def _urlopen_response(status=202, body=None):
    response = MagicMock()
    response.status = status
    response.read.return_value = json.dumps(body or {
        "status": "PROCESSED",
        "occurrence_id": "occ-123",
        "correlation_id": "corr-456",
        "action": "MONITOR",
        "priority": "NORMAL",
        "responsible_team": "SINDICANCIA",
        "sla_minutes": 1440,
        "alert_required": False,
        "diagnostic_summary": "NOISE/LOW: encaminhar para SINDICANCIA.",
        "audit_record_id": "flowise-corr-456",
        "processed_at": "2026-08-25T19:00:00Z",
    }).encode("utf-8")
    context = MagicMock()
    context.__enter__.return_value = response
    return context


def test_sends_post_with_minimal_payload_and_correlation_id(monkeypatch):
    monkeypatch.setenv("FLOWISE_WEBHOOK_URL", "https://flowise.example/webhook")
    with patch(
        "condominium_incident_agent.tools.flowise_webhook.urlopen",
        return_value=_urlopen_response(),
    ) as mocked_urlopen:
        result = send_to_flowise(_state())

    request = mocked_urlopen.call_args.args[0]
    assert request.method == "POST"
    assert request.full_url == "https://flowise.example/webhook"
    assert request.headers["Content-type"] == "application/json"
    assert __import__("json").loads(request.data) == {
        "occurrence_id": "occ-123",
        "correlation_id": "corr-456",
        "reported_at": "2026-08-23T12:00:00Z",
        "category": "NOISE",
        "severity": "LOW",
        "summary": "Barulho excessivo.",
        "involved_people": ["Joao"],
        "apartment": "302",
        "building": "A",
    }
    assert result["flowise_delivery_status"] == "SENT"
    assert result["flowise_action"] == "MONITOR"
    assert result["flowise_triage"]["responsible_team"] == "SINDICANCIA"
    assert result["flowise_triage"]["audit_record_id"] == "flowise-corr-456"


def test_invalid_payload_is_blocked_before_http(monkeypatch):
    monkeypatch.setenv("FLOWISE_WEBHOOK_URL", "https://flowise.example/webhook")
    with patch("condominium_incident_agent.tools.flowise_webhook.urlopen") as mocked_urlopen:
        result = send_to_flowise(_state(category="INVALID"))

    mocked_urlopen.assert_not_called()
    assert result["flowise_delivery_status"] == "BLOCKED"


def test_payload_validation_rejects_missing_correlation_id():
    with pytest.raises(ValueError):
        build_flowise_payload(_state(correlation_id=None))


def test_timeout_is_reported_as_failed(monkeypatch, caplog):
    monkeypatch.setenv("FLOWISE_WEBHOOK_URL", "https://flowise.example/webhook")
    with patch(
        "condominium_incident_agent.tools.flowise_webhook.urlopen",
        side_effect=TimeoutError,
    ):
        result = send_to_flowise(_state())

    assert result["flowise_delivery_status"] == "FAILED"
    assert "timeout" in result["flowise_delivery_error"]
    assert "Flowise delivery failed" in caplog.text


def test_flowise_result_is_persisted_in_occurrence_report(tmp_path, monkeypatch):
    monkeypatch.setenv("FLOWISE_WEBHOOK_URL", "https://flowise.example/webhook")
    report = Path(tmp_path) / "occurrence.json"
    report.write_text(json.dumps({"occurrence_id": "occ-123"}), encoding="utf-8")
    with patch(
        "condominium_incident_agent.tools.flowise_webhook.urlopen",
        return_value=_urlopen_response(),
    ):
        send_to_flowise(_state(output_file=str(report)))

    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["flowise_status"] == "PROCESSED"
    assert data["flowise_action"] == "MONITOR"
    assert data["flowise_correlation_id"] == "corr-456"
    assert data["flowise_triage"]["sla_minutes"] == 1440


def test_flowise_output_is_sanitized_before_state_and_persistence(tmp_path, monkeypatch):
    monkeypatch.setenv("FLOWISE_WEBHOOK_URL", "https://flowise.example/webhook")
    report = tmp_path / "occurrence.json"
    report.write_text(json.dumps({"occurrence_id": "occ-123"}), encoding="utf-8")
    response_body = {
        "status": "PROCESSED",
        "occurrence_id": "occ-123",
        "correlation_id": "corr-456",
        "action": "MONITOR",
        "priority": "NORMAL",
        "responsible_team": "SINDICANCIA",
        "sla_minutes": 1440,
        "alert_required": False,
        "diagnostic_summary": "Diagnóstico token=external-secret",
        "audit_record_id": "flowise-corr-456",
        "processed_at": "2026-08-25T19:00:00Z",
    }
    with patch(
        "condominium_incident_agent.tools.flowise_webhook.urlopen",
        return_value=_urlopen_response(body=response_body),
    ):
        result = send_to_flowise(_state(output_file=str(report)))

    persisted = json.loads(report.read_text(encoding="utf-8"))
    assert "external-secret" not in result["flowise_triage"]["diagnostic_summary"]
    assert "[REDACTED]" in result["flowise_triage"]["diagnostic_summary"]
    assert "external-secret" not in json.dumps(persisted, ensure_ascii=False)


def test_mismatched_flowise_correlation_is_rejected(monkeypatch):
    monkeypatch.setenv("FLOWISE_WEBHOOK_URL", "https://flowise.example/webhook")
    with patch(
        "condominium_incident_agent.tools.flowise_webhook.urlopen",
        return_value=_urlopen_response(body={
            "status": "PROCESSED",
            "occurrence_id": "occ-123",
            "correlation_id": "other-correlation",
            "action": "MONITOR",
        }),
    ):
        result = send_to_flowise(_state())

    assert result["flowise_delivery_status"] == "FAILED"
    assert result["flowise_delivery_error"] == "Correlação inválida na resposta."


def test_http_error_is_reported_as_failed(monkeypatch):
    monkeypatch.setenv("FLOWISE_WEBHOOK_URL", "https://flowise.example/webhook")
    error = HTTPError("https://flowise.example/webhook", 503, "unavailable", {}, None)
    with patch(
        "condominium_incident_agent.tools.flowise_webhook.urlopen",
        side_effect=error,
    ):
        result = send_to_flowise(_state())

    assert result["flowise_delivery_status"] == "FAILED"
    assert result["flowise_delivery_error"] == "HTTP 503"


def test_failed_persistence_blocks_external_send(monkeypatch):
    with patch("condominium_incident_agent.nodes.send_to_flowise.send_occurrence_to_flowise") as send:
        result = send_to_flowise(_state(output_file=None, classification_error="blocked"))

    send.assert_not_called()
    assert result["flowise_delivery_status"] == "BLOCKED"


def test_invalid_timeout_configuration_is_controlled(monkeypatch):
    monkeypatch.setenv("FLOWISE_WEBHOOK_URL", "https://flowise.example/webhook")
    monkeypatch.setenv("FLOWISE_TIMEOUT_SECONDS", "invalid")

    result = send_to_flowise(_state())

    assert result["flowise_delivery_status"] == "BLOCKED"
    assert result["flowise_delivery_error"] == "Payload inválido ou configuração inválida."


def test_flowise_unavailable_does_not_remove_saved_occurrence(tmp_path, monkeypatch):
    monkeypatch.setenv("FLOWISE_WEBHOOK_URL", "https://flowise.example/webhook")
    report = tmp_path / "occurrence.json"
    report.write_text(json.dumps({"occurrence_id": "occ-123"}), encoding="utf-8")
    with patch(
        "condominium_incident_agent.tools.flowise_webhook.urlopen",
        side_effect=OSError,
    ):
        result = send_to_flowise(_state(output_file=str(report)))

    assert result["flowise_delivery_status"] == "FAILED"
    assert report.exists()
    assert json.loads(report.read_text(encoding="utf-8"))["flowise_delivery_status"] == "FAILED"


def test_rejected_workflow_result_is_a_controlled_failure(monkeypatch):
    monkeypatch.setenv("FLOWISE_WEBHOOK_URL", "https://flowise.example/webhook")
    with patch(
        "condominium_incident_agent.tools.flowise_webhook.urlopen",
        return_value=_urlopen_response(body={
            "status": "REJECTED",
            "occurrence_id": "occ-123",
            "correlation_id": "corr-456",
            "error": ["payload rejeitado"],
        }),
    ):
        result = send_to_flowise(_state())

    assert result["flowise_delivery_status"] == "FAILED"
    assert result["flowise_delivery_error"] == "Processamento rejeitado pelo Flowise."


def test_exported_workflow_has_webhook_processing_and_observable_output():
    workflow_path = Path(__file__).parents[2] / "flowise" / "workflow.json"
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    nodes = {node["id"]: node for node in workflow["nodes"]}

    start_inputs = nodes["startAgentflow_0"]["data"]["inputs"]
    assert start_inputs["startInputType"] == "webhookTrigger"
    assert start_inputs["webhookMethod"] == "POST"
    validation = nodes["customFunctionAgentflow_0"]["data"]
    assert validation["name"] == "customFunctionAgentflow"
    assert validation["inputs"]["customFunctionInputVariables"] == [
        {"variableName": "rawInput", "variableValue": "{{$webhook.body}}"}
    ]
    assert "correlation_id" in validation["inputs"]["customFunctionJavascriptFunction"]
    triage_code = nodes["customFunctionAgentflow_1"]["data"]["inputs"][
        "customFunctionJavascriptFunction"
    ]
    assert 'data-id="customFunctionAgentflow_0"' in nodes["customFunctionAgentflow_1"][
        "data"
    ]["inputs"]["customFunctionInputVariables"][0]["variableValue"]
    assert "customFunctionAgentflow_0.output.content" in nodes[
        "customFunctionAgentflow_1"
    ]["data"]["inputs"]["customFunctionInputVariables"][0]["variableValue"]
    assert "responsible_team" in triage_code
    assert "sla_minutes" in triage_code
    audit_code = nodes["customFunctionAgentflow_2"]["data"]["inputs"][
        "customFunctionJavascriptFunction"
    ]
    assert "audit_record_id" in audit_code
    assert 'data-id="customFunctionAgentflow_1"' in nodes["customFunctionAgentflow_2"][
        "data"
    ]["inputs"]["customFunctionInputVariables"][0]["variableValue"]
    assert "customFunctionAgentflow_1.output.content" in nodes[
        "customFunctionAgentflow_2"
    ]["data"]["inputs"]["customFunctionInputVariables"][0]["variableValue"]
    assert nodes["directReplyAgentflow_0"]["data"]["inputs"]["directReplyMessage"] == (
        '<p><span class="variable" data-type="mention" '
        'data-id="customFunctionAgentflow_2" data-label="customFunctionAgentflow_2">'
        "{{ customFunctionAgentflow_2.output.content }}</span></p>"
    )

    assert all(isinstance(node["data"]["inputParams"], list) for node in workflow["nodes"])

    node_ids = set(nodes)
    assert all(edge["source"] in node_ids and edge["target"] in node_ids for edge in workflow["edges"])
