"""Tool responsável por consultar o histórico de ocorrências da sessão."""

import logging

from langchain_core.tools import tool

from incident_classification_agent.session import load_session

logger = logging.getLogger(__name__)


@tool
def get_session_history(apartment: str, building: str | None = None) -> dict:
    """Consulta o histórico de ocorrências anteriores de um apartamento.

    Deve ser chamada quando o relato mencionar um apartamento, para verificar
    se já houve ocorrências anteriores que possam indicar reincidência.
    O histórico consultado influencia diretamente a classificação de severidade:
    reincidências da mesma categoria elevam a severidade da ocorrência atual.

    Args:
        apartment: Número do apartamento (ex: "305", "101").
        building: Bloco ou torre do apartamento (ex: "A", "B"). Opcional.

    Returns:
        Dicionário com:
        - ``found``: True se houver ocorrências anteriores, False caso contrário.
        - ``apartment``: Apartamento consultado.
        - ``building``: Bloco consultado.
        - ``occurrences``: Lista de ocorrências anteriores. Cada entrada contém
          ``occurrence_id``, ``reported_at``, ``category``, ``severity``,
          ``summary``.
        - ``total``: Total de ocorrências encontradas.
        - ``message``: Mensagem descritiva do resultado.
    """
    records = load_session()

    matches = []
    for record in records:
        apt_match = (
            record.get("apartment", "").strip().lower() == apartment.strip().lower()
        )
        building_match = (
            building is None
            or record.get("building", "").strip().lower()
            == (building or "").strip().lower()
        )
        if apt_match and building_match:
            matches.append(
                {
                    "occurrence_id": record.get("occurrence_id"),
                    "reported_at": record.get("reported_at"),
                    "category": record.get("category"),
                    "severity": record.get("severity"),
                    "summary": record.get("summary"),
                }
            )

    if not matches:
        logger.info(
            "No session history for apartment %s / building %s", apartment, building
        )
        return {
            "found": False,
            "apartment": apartment,
            "building": building,
            "occurrences": [],
            "total": 0,
            "message": "Nenhuma ocorrência anterior registrada para este apartamento.",
        }

    logger.info(
        "Session history found — apartment: %s, building: %s, total: %d",
        apartment,
        building,
        len(matches),
    )
    return {
        "found": True,
        "apartment": apartment,
        "building": building,
        "occurrences": matches,
        "total": len(matches),
        "message": f"{len(matches)} ocorrência(s) anterior(es) encontrada(s).",
    }
