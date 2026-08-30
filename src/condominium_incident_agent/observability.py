"""Observabilidade operacional e auditoria independente do agente."""

from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from typing import Any

from condominium_incident_agent.state import AgentState

logger = logging.getLogger(__name__)
def _value(value: Any) -> Any:
    return getattr(value, "value", value)


def _safe_result(state: AgentState | None) -> dict[str, Any]:
    """Retorna somente metadados de decisão, sem conteúdo do relato/prompt."""
    if not state:
        return {}
    return {
        "category": _value(state.get("category")),
        "severity": _value(state.get("severity")),
        "multiple_incidents_detected": state.get("multiple_incidents_detected"),
        "classification_error": bool(state.get("classification_error")),
        "output_file": state.get("output_file"),
        "escalated": bool(state.get("escalated_file")),
        "flowise_delivery_status": state.get("flowise_delivery_status"),
        "flowise_status": state.get("flowise_status"),
        "flowise_action": state.get("flowise_action"),
    }


class _ExecutionRecorder:
    """Armazena logs e auditoria em coleções separadas e protegidas."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._logs: list[dict[str, Any]] = []
        self._audit: list[dict[str, Any]] = []

    def log(self, record: dict[str, Any]) -> None:
        with self._lock:
            self._logs.append(dict(record))

    def audit(self, record: dict[str, Any]) -> None:
        with self._lock:
            self._audit.append(dict(record))

    def investigate(self, correlation_id: str) -> dict[str, list[dict[str, Any]]]:
        with self._lock:
            return {
                "logs": [r.copy() for r in self._logs if r.get("correlation_id") == correlation_id],
                "audit": [r.copy() for r in self._audit if r.get("correlation_id") == correlation_id],
            }

    def clear(self) -> None:
        with self._lock:
            self._logs.clear()
            self._audit.clear()


_RECORDER = _ExecutionRecorder()


def clear_observability() -> None:
    """Limpa o recorder in-memory, principalmente para testes e processos curtos."""
    _RECORDER.clear()


def investigate_execution(correlation_id: str) -> dict[str, list[dict[str, Any]]]:
    """Consulta os registros operacionais e de auditoria por execução."""
    return _RECORDER.investigate(correlation_id)


def _record(correlation_id: str, node: str, event: str, **fields: Any) -> None:
    record = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "correlation_id": correlation_id,
        "node": node,
        "event": event,
        **fields,
    }
    _RECORDER.log(record)
    logger.info("agent_observation %s", json.dumps(record, ensure_ascii=False, default=str))


def instrument_node(node_name: str, node: Callable[..., Any]) -> Callable[..., Any]:
    """Instrumenta um node sem alterar sua assinatura ou retorno."""
    @wraps(node)
    def wrapped(state: AgentState, *args: Any, **kwargs: Any) -> AgentState:
        correlation_id = state.get("correlation_id", "unknown")
        started = time.perf_counter()
        _record(correlation_id, node_name, "started")
        try:
            result = node(state, *args, **kwargs)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started) * 1000, 3)
            fields = {"duration_ms": duration_ms, "error": type(exc).__name__}
            _record(correlation_id, node_name, "failed", **fields)
            _RECORDER.audit({
                "timestamp": datetime.now(tz=UTC).isoformat(),
                "correlation_id": correlation_id,
                "node": node_name,
                "event": "node_failed",
                **fields,
            })
            raise

        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        fields = {"duration_ms": duration_ms, "result": _safe_result(result)}
        _record(correlation_id, node_name, "completed", **fields)
        _RECORDER.audit({
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "correlation_id": correlation_id,
            "node": node_name,
            "event": "node_completed",
            **fields,
        })
        return result

    return wrapped