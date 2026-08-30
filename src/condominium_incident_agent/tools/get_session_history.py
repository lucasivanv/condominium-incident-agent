"""Tool responsável por consultar o histórico de ocorrências da sessão."""

import logging

from langchain_core.tools import tool

from condominium_incident_agent.session import (
    RECENT_CONTEXT_LIMIT,
    find_session_records,
    load_session,
)

logger = logging.getLogger(__name__)


@tool
def get_session_history(apartment: str, building: str | None = None) -> dict:
    """Consulta o histórico de ocorrências anteriores de um apartamento.

    Deve ser chamada quando o relato mencionar um apartamento, para verificar
    se já houve ocorrências anteriores que possam indicar reincidência.
    O histórico consultado influencia diretamente a classificação de severidade:
    reincidências da mesma categoria elevam a severidade da ocorrência atual.

    Retorna no máximo as ``RECENT_CONTEXT_LIMIT`` ocorrências mais recentes
    para o apartamento, evitando injeção excessiva de contexto no prompt.

    Args:
        apartment: Número do apartamento (ex: "305", "101").
        building: Bloco ou torre do apartamento (ex: "A", "B"). Opcional.

    Returns:
        Dicionário com:
        - ``found``: True se houver ocorrências anteriores, False caso contrário.
        - ``apartment``: Apartamento consultado.
        - ``building``: Bloco consultado.
        - ``occurrences``: Lista das ocorrências mais recentes (limitada a
          ``RECENT_CONTEXT_LIMIT``). Cada entrada contém ``occurrence_id``,
          ``reported_at``, ``category``, ``severity``, ``summary``.
        - ``total``: Total de ocorrências encontradas (antes da limitação).
        - ``returned``: Quantidade efetivamente retornada após o limite.
        - ``message``: Mensagem descritiva do resultado.
    """
    records = load_session()

    matches = [
        {
            "occurrence_id": record.get("occurrence_id"),
            "reported_at": record.get("reported_at"),
            "category": record.get("category"),
            "severity": record.get("severity"),
            "summary": record.get("summary"),
        }
        for record in find_session_records(records, apartment, building)
    ]

    total = len(matches)

    if not matches:
        logger.info("No session history for apartment %s / building %s", apartment, building)
        return {
            "found": False,
            "apartment": apartment,
            "building": building,
            "occurrences": [],
            "total": 0,
            "returned": 0,
            "message": "Nenhuma ocorrência anterior registrada para este apartamento.",
        }

    # Retorna apenas as ocorrências mais recentes dentro do limite.
    # A lista já está na ordem de inserção (cronológica), portanto as
    # mais recentes ficam ao final — usamos as últimas N entradas.
    limited = matches[-RECENT_CONTEXT_LIMIT:]
    returned = len(limited)

    logger.info(
        "Session history found — apartment: %s, building: %s, total: %d, returned: %d",
        apartment,
        building,
        total,
        returned,
    )

    truncation_note = (
        f" (exibindo as {returned} mais recentes de {total})"
        if total > returned
        else ""
    )
    return {
        "found": True,
        "apartment": apartment,
        "building": building,
        "occurrences": limited,
        "total": total,
        "returned": returned,
        "message": f"{total} ocorrência(s) anterior(es) encontrada(s){truncation_note}.",
    }
