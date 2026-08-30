"""Nó responsável por persistir a ocorrência em disco."""

import json
import logging
import os
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

from condominium_incident_agent.security import (
    has_valid_human_approval,
    is_critical_action,
    sanitize_untrusted_data,
    sanitize_untrusted_text,
)
from condominium_incident_agent.session import append_to_session
from condominium_incident_agent.state import AgentState

logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).parent.parent.parent.parent
REPORTS_DIR = _BASE_DIR / "reports"
ESCALATED_DIR = REPORTS_DIR / "escalated"


def _sanitize_optional_text(value: object) -> str | None:
    """Sanitiza campos textuais opcionais antes de qualquer persistência."""
    return sanitize_untrusted_text(str(value)) if value is not None else None


def _write_json_atomic(path: Path, payload: dict) -> None:
    """Escreve um JSON e substitui o destino somente após concluir a escrita."""
    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def save_occurrence(state: AgentState) -> AgentState:
    """Persiste a ocorrência em disco injetando os campos de contexto do estado.

    A classificação (category, severity, summary, etc.) foi extraída pelo LLM
    via tool call e já está no estado. Este nó combina esses dados com os
    campos de contexto imutáveis (occurrence_id, user_input, reported_by,
    reported_at, resident_info) e grava o arquivo JSON final.

    Além do arquivo individual, atualiza o ``session.json`` acumulativo com
    uma entrada resumida da ocorrência, usada pela tool ``get_session_history``
    para consulta de reincidência em interações futuras.

    Incidentes com severidade HIGH são adicionalmente copiados para
    reports/escalated/ com flag de escalonamento.

    Args:
        state: Estado atual do agente com todos os campos preenchidos.

    Returns:
        Estado atualizado com ``output_file``, ``escalated_file`` e
        ``session_history`` refletindo o acumulado da sessão corrente.
    """
    if is_critical_action(state.get("severity")) and not has_valid_human_approval(state):
        logger.warning(
            "Critical action blocked without valid human approval for %s",
            state.get("occurrence_id"),
        )
        return {
            **state,
            "classification_error": (
                "Ação crítica bloqueada: aprovação humana válida ausente ou expirada."
            ),
            "output_file": None,
            "escalated_file": None,
        }
    try:
        return _save_occurrence(state)
    except (OSError, ValueError, TypeError) as exc:
        error = f"Falha controlada ao persistir a ocorrência: {type(exc).__name__}."
        logger.exception("Occurrence persistence failed for %s", state.get("occurrence_id"))
        return {
            **state,
            "classification_error": error,
            "output_file": None,
            "escalated_file": None,
        }


def update_occurrence_flowise_result(state: AgentState) -> None:
    """Atualiza o relatório salvo com o resultado da automação externa."""
    output_file = state.get("output_file")
    if not output_file:
        return
    path = Path(output_file)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.update(
        {
            "flowise_status": state.get("flowise_status"),
            "flowise_action": state.get("flowise_action"),
            "flowise_correlation_id": state.get("correlation_id"),
            "flowise_processed_at": state.get("flowise_processed_at"),
            "flowise_delivery_status": state.get("flowise_delivery_status"),
            "flowise_error": sanitize_untrusted_data(state.get("flowise_delivery_error")),
            "flowise_triage": sanitize_untrusted_data(state.get("flowise_triage")),
        }
    )
    _write_json_atomic(path, payload)


def _save_occurrence(state: AgentState) -> AgentState:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    occurrence_id = state.get("occurrence_id") or str(uuid.uuid4())
    category = state.get("category")
    severity = state.get("severity")

    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    filename = f"{timestamp}_{occurrence_id}.json"

    payload = {
        "occurrence_id": occurrence_id,
        "reported_by": sanitize_untrusted_text(state.get("reported_by") or ""),
        "reported_at": state.get("reported_at"),
        "user_input": sanitize_untrusted_text(state.get("user_input") or ""),
        "category": category.value if category is not None else None,
        "severity": severity.value if severity is not None else None,
        "involved_people": sanitize_untrusted_data(state.get("involved_people") or []),
        "apartment": _sanitize_optional_text(state.get("apartment")),
        "building": _sanitize_optional_text(state.get("building")),
        "summary": sanitize_untrusted_text(state.get("summary") or ""),
        "resident_info": sanitize_untrusted_data(state.get("resident_info")),
        "saved_at": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    output_path = REPORTS_DIR / filename
    _write_json_atomic(output_path, payload)
    logger.info("Occurrence saved to %s", output_path)

    # Entrada resumida para o histórico de sessão — usada por get_session_history
    session_entry = {
        "occurrence_id": occurrence_id,
        "reported_at": state.get("reported_at"),
        "reported_by": sanitize_untrusted_text(state.get("reported_by") or ""),
        "category": category.value if category is not None else None,
        "severity": severity.value if severity is not None else None,
        "summary": sanitize_untrusted_text(state.get("summary") or ""),
        "apartment": _sanitize_optional_text(state.get("apartment")),
        "building": _sanitize_optional_text(state.get("building")),
    }
    append_to_session(session_entry)

    # Atualiza o session_history em memória no estado do agente
    session_history = list(state.get("session_history") or [])
    session_history.append(session_entry)

    result: dict = {
        "output_file": str(output_path),
        "escalated_file": None,
        "session_history": session_history,
    }

    severity_value = severity.value if severity is not None else None
    if severity_value == "HIGH":
        ESCALATED_DIR.mkdir(parents=True, exist_ok=True)
        escalated_path = ESCALATED_DIR / filename
        escalated_payload = {
            **payload,
            "escalated": True,
            "escalated_at": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        _write_json_atomic(escalated_path, escalated_payload)
        logger.warning("HIGH severity — occurrence escalated to %s", escalated_path)
        result["escalated_file"] = str(escalated_path)

    return {**state, **result}
