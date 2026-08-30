"""Nó que encaminha somente ocorrências autorizadas ao Flowise."""

import logging

from condominium_incident_agent.nodes.save_occurrence import (
    update_occurrence_flowise_result,
)
from condominium_incident_agent.security import sanitize_untrusted_data
from condominium_incident_agent.state import AgentState
from condominium_incident_agent.tools.flowise_webhook import send_occurrence_to_flowise

logger = logging.getLogger(__name__)


def send_to_flowise(state: AgentState) -> AgentState:
    """Executa o envio após persistência e mantém falhas como erro controlado."""
    if state.get("classification_error") or not state.get("output_file"):
        return {
            **state,
            "flowise_delivery_status": "BLOCKED",
            "flowise_delivery_error": None,
            "flowise_status": None,
            "flowise_action": None,
            "flowise_processed_at": None,
            "flowise_triage": None,
        }

    try:
        result = send_occurrence_to_flowise(state)
    except (TypeError, ValueError) as exc:
        logger.error(
            "Flowise delivery blocked (correlation_id=%s, error=%s)",
            state.get("correlation_id"),
            type(exc).__name__,
        )
        return {
            **state,
            "flowise_delivery_status": "BLOCKED",
            "flowise_delivery_error": "Payload inválido ou configuração inválida.",
            "flowise_status": None,
            "flowise_action": None,
            "flowise_processed_at": None,
            "flowise_triage": None,
        }

    updated_state = {
        **state,
        "flowise_delivery_status": result["status"],
        "flowise_delivery_error": result["error"],
        "flowise_status": result.get("flowise_status"),
        "flowise_action": result.get("flowise_action"),
        "flowise_processed_at": result.get("flowise_processed_at"),
        "flowise_triage": sanitize_untrusted_data(result.get("flowise_triage")),
    }
    try:
        update_occurrence_flowise_result(updated_state)
    except (OSError, ValueError, TypeError) as exc:
        logger.error(
            "Flowise result persistence failed (correlation_id=%s, error=%s)",
            state.get("correlation_id"),
            type(exc).__name__,
        )
    return updated_state
