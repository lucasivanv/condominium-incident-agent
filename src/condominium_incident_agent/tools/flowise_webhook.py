"""Tool HTTP determinística para encaminhar ocorrências autorizadas."""

from __future__ import annotations

import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field, field_validator

from condominium_incident_agent.security import (
    sanitize_untrusted_data,
    sanitize_untrusted_text,
)
from condominium_incident_agent.state import AgentState

logger = logging.getLogger(__name__)


class FlowiseOccurrencePayload(BaseModel):
    """Contrato mínimo enviado ao webhook externo."""

    model_config = ConfigDict(extra="forbid")

    occurrence_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    reported_at: str = Field(min_length=1)
    category: str = Field(min_length=1)
    severity: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    involved_people: list[str]
    apartment: str | None = None
    building: str | None = None

    @field_validator("category")
    @classmethod
    def reject_category_values(cls, value: str) -> str:
        if value not in {"ACCESS", "PACKAGE", "NOISE", "MAINTENANCE", "SECURITY", "OTHER"}:
            raise ValueError("Valor de classificação inválido.")
        return value

    @field_validator("severity")
    @classmethod
    def reject_severity_values(cls, value: str) -> str:
        if value not in {"LOW", "MEDIUM", "HIGH"}:
            raise ValueError("Valor de severidade inválido.")
        return value


class FlowiseProcessingResult(BaseModel):
    """Resposta operacional esperada do workflow externo."""

    model_config = ConfigDict(extra="ignore")

    status: str = Field(min_length=1)
    occurrence_id: str | None = None
    correlation_id: str | None = None
    action: str | None = None
    priority: str | None = None
    responsible_team: str | None = None
    sla_minutes: int | None = Field(default=None, ge=0)
    alert_required: bool | None = None
    diagnostic_summary: str | None = None
    audit_record_id: str | None = None
    error: list[str] | str | None = None
    processed_at: str | None = None


def build_flowise_payload(state: AgentState) -> dict:
    """Valida e monta o payload sem expor relato, morador ou aprovação."""
    category = state.get("category")
    severity = state.get("severity")
    payload = FlowiseOccurrencePayload(
        occurrence_id=state.get("occurrence_id"),
        correlation_id=state.get("correlation_id"),
        reported_at=state.get("reported_at"),
        category=category.value if hasattr(category, "value") else category,
        severity=severity.value if hasattr(severity, "value") else severity,
        summary=sanitize_untrusted_text(state.get("summary") or ""),
        involved_people=sanitize_untrusted_data(state.get("involved_people") or []),
        apartment=state.get("apartment"),
        building=state.get("building"),
    )
    return payload.model_dump()


def _parse_flowise_response(raw_body: bytes) -> FlowiseProcessingResult:
    """Interpreta resposta JSON direta ou texto JSON retornado pelo Flowise."""
    body = raw_body.decode("utf-8", errors="replace")

    response = json.loads(body)

    if isinstance(response, dict) and isinstance(response.get("text"), str):
        response = json.loads(response["text"])

    return FlowiseProcessingResult.model_validate(response)


def send_occurrence_to_flowise(state: AgentState) -> dict:
    """Envia uma ocorrência já persistida para o webhook configurado."""
    payload = build_flowise_payload(state)
    endpoint = os.environ.get("FLOWISE_WEBHOOK_URL", "").strip()
    if not endpoint:
        logger.info(
            "Flowise delivery skipped: endpoint not configured (correlation_id=%s)",
            state.get("correlation_id"),
        )
        return {"status": "NOT_CONFIGURED", "error": None}

    try:
        timeout = float(os.environ.get("FLOWISE_TIMEOUT_SECONDS", "10"))
    except ValueError as exc:
        raise ValueError("FLOWISE_TIMEOUT_SECONDS inválido.") from exc
    if timeout <= 0:
        raise ValueError("FLOWISE_TIMEOUT_SECONDS deve ser positivo.")

    request = Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            if not 200 <= response.status < 300:
                logger.error(
                    "Flowise delivery failed (correlation_id=%s, error=HTTPError)",
                    state.get("correlation_id"),
                )
                return {"status": "FAILED", "error": f"HTTP {response.status}"}

            raw_body = response.read()

            logger.info(
                "Flowise HTTP response — status=%s, content_type=%s",
                response.status,
                response.headers.get("Content-Type"),
            )

            try:
                flowise_result = _parse_flowise_response(raw_body)
            except (json.JSONDecodeError, TypeError, ValueError):
                logger.error(
                    "Flowise response invalid (correlation_id=%s)",
                    state.get("correlation_id"),
                )
                return {
                    "status": "FAILED",
                    "error": "Resposta inválida do Flowise.",
                }
            if flowise_result.correlation_id != state.get("correlation_id"):
                logger.error(
                    "Flowise correlation mismatch (correlation_id=%s)",
                    state.get("correlation_id"),
                )
                return {"status": "FAILED", "error": "Correlação inválida na resposta."}
            if flowise_result.occurrence_id != state.get("occurrence_id"):
                logger.error(
                    "Flowise occurrence mismatch (correlation_id=%s)",
                    state.get("correlation_id"),
                )
                return {"status": "FAILED", "error": "Ocorrência inválida na resposta."}
            if flowise_result.status != "PROCESSED":
                logger.error(
                    "Flowise processing rejected (correlation_id=%s, flowise_status=%s)",
                    state.get("correlation_id"),
                    flowise_result.status,
                )
                return {"status": "FAILED", "error": "Processamento rejeitado pelo Flowise."}
    except HTTPError as exc:
        logger.error(
            "Flowise delivery failed (correlation_id=%s, error=HTTPError)",
            state.get("correlation_id"),
        )
        return {"status": "FAILED", "error": f"HTTP {exc.code}"}
    except (TimeoutError, URLError, OSError):
        logger.error(
            "Flowise delivery failed (correlation_id=%s, error=connection)",
            state.get("correlation_id"),
        )
        return {"status": "FAILED", "error": "Falha de conexão ou timeout."}

    logger.info(
        "Flowise delivery succeeded (correlation_id=%s, flowise_status=%s, action=%s)",
        state.get("correlation_id"),
        flowise_result.status,
        flowise_result.action,
    )
    return {
        "status": "SENT",
        "error": None,
        "flowise_status": flowise_result.status,
        "flowise_action": flowise_result.action,
        "flowise_processed_at": flowise_result.processed_at,
        "flowise_triage": {
            "priority": flowise_result.priority,
            "responsible_team": flowise_result.responsible_team,
            "sla_minutes": flowise_result.sla_minutes,
            "alert_required": flowise_result.alert_required,
            "diagnostic_summary": flowise_result.diagnostic_summary,
            "audit_record_id": flowise_result.audit_record_id,
        },
    }
