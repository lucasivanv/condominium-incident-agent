"""Controles determinísticos para entradas não confiáveis e ações críticas."""

import hashlib
import hmac
import os
import re
from datetime import UTC, datetime

from condominium_incident_agent.enums import Severity

_ALLOWED_READ_TOOLS = {"lookup_resident", "get_session_history"}

_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(?:bearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)\b(?:api[_ -]?key|token|secret|password|senha)\s*[:=]\s*[^\s,;]+"),
)


def sanitize_untrusted_text(value: str) -> str:
    """Redige credenciais comuns sem interpretar comandos contidos no relato."""
    sanitized = value
    for pattern in _SECRET_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)
    return sanitized


def sanitize_untrusted_data(value: object) -> object:
    """Redige strings em estruturas retornadas por entradas ou tools."""
    if isinstance(value, str):
        return sanitize_untrusted_text(value)
    if isinstance(value, dict):
        return {key: sanitize_untrusted_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_untrusted_data(item) for item in value]
    return value


def authorize_tool_call(tool_name: str, arguments: dict) -> None:
    """Permite somente consultas conhecidas com argumentos básicos válidos."""
    if tool_name not in _ALLOWED_READ_TOOLS:
        raise PermissionError(f"Tool não autorizada: {tool_name}.")
    if not isinstance(arguments, dict):
        raise PermissionError(f"Argumentos inválidos para a tool {tool_name}.")
    apartment = arguments.get("apartment")
    building = arguments.get("building")
    if not isinstance(apartment, str) or not apartment.strip():
        raise PermissionError(f"Apartamento obrigatório para a tool {tool_name}.")
    if building is not None and not isinstance(building, str):
        raise PermissionError(f"Bloco inválido para a tool {tool_name}.")


def is_critical_action(severity: Severity | str | None) -> bool:
    """Retorna se o nível exige aprovação humana antes da persistência."""
    value = severity.value if isinstance(severity, Severity) else severity
    return value == Severity.HIGH.value


def _approval_secret() -> bytes:
    return os.environ.get("HUMAN_APPROVAL_SECRET", "").encode("utf-8")


def create_human_approval(
    occurrence_id: str, approved_by: str, expires_at: str
) -> dict[str, str]:
    """Cria uma aprovação externa assinada para uso em testes ou integração."""
    secret = _approval_secret()
    if not secret:
        raise ValueError("HUMAN_APPROVAL_SECRET não configurado.")
    payload = f"{occurrence_id}|{approved_by}|{expires_at}".encode()
    token = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return {
        "status": "APPROVED",
        "approved_by": approved_by,
        "approved_at": datetime.now(tz=UTC).isoformat(),
        "expires_at": expires_at,
        "token": token,
    }


def has_valid_human_approval(state: dict, now: datetime | None = None) -> bool:
    """Valida aprovação sem confiar em campos produzidos pelo LLM ou relato."""
    approval = state.get("human_approval")
    occurrence_id = state.get("occurrence_id")
    secret = _approval_secret()
    if not isinstance(approval, dict) or not occurrence_id or not secret:
        return False
    if approval.get("status") != "APPROVED":
        return False
    approved_by = approval.get("approved_by")
    expires_at = approval.get("expires_at")
    token = approval.get("token")
    if not all(isinstance(item, str) and item for item in (approved_by, expires_at, token)):
        return False
    try:
        expiry = datetime.fromisoformat(expires_at)
    except ValueError:
        return False
    current_time = now or datetime.now(tz=UTC)
    if expiry.tzinfo is None or expiry <= current_time.astimezone(UTC):
        return False
    payload = f"{occurrence_id}|{approved_by}|{expires_at}".encode()
    expected = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(token, expected)