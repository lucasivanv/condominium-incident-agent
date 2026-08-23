"""Tool responsável por consultar dados de moradores cadastrados."""

import json
import logging
from pathlib import Path

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_DATA_PATH = Path(__file__).parent.parent.parent.parent / "data" / "residents.json"


def _load_residents() -> list[dict]:
    """Carrega a lista de moradores do arquivo local.

    Returns:
        Lista de dicionários com os dados dos moradores.
    """
    if not _DATA_PATH.exists():
        logger.warning("residents.json not found at %s", _DATA_PATH)
        return []
    try:
        return json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load residents.json: %s", exc)
        return []


@tool
def lookup_resident(apartment: str, building: str | None = None) -> dict:
    """Consulta os dados cadastrais do morador de um apartamento específico.

    Útil para verificar se o apartamento existe no condomínio, confirmar o
    nome do morador e checar se ele possui visitantes ou veículos autorizados.

    Args:
        apartment: Número do apartamento (ex: "402", "101-B").
        building: Bloco ou torre do apartamento (ex: "A", "Torre 1"). Opcional.

    Returns:
        Dicionário com os dados do morador encontrado, ou com ``found=False``
        caso o apartamento não esteja cadastrado. Estrutura quando encontrado:
        - ``found``: True
        - ``apartment``: número do apartamento
        - ``building``: bloco/torre
        - ``resident_name``: nome do morador
        - ``authorized_visitors``: lista de visitantes pré-autorizados
        - ``vehicles``: lista de placas de veículos cadastrados
        - ``phone``: telefone de contato (mascarado)
    """
    residents = _load_residents()

    for resident in residents:
        apt_match = (
            resident.get("apartment", "").strip().lower() == apartment.strip().lower()
        )
        building_match = (
            building is None
            or resident.get("building", "").strip().lower() == building.strip().lower()
        )
        if apt_match and building_match:
            logger.info(
                "Resident found for apartment %s / building %s", apartment, building
            )
            return {
                "found": True,
                "apartment": resident.get("apartment"),
                "building": resident.get("building"),
                "resident_name": resident.get("resident_name"),
                "authorized_visitors": resident.get("authorized_visitors", []),
                "vehicles": resident.get("vehicles", []),
                "phone": resident.get("phone"),
            }

    logger.info("No resident found for apartment %s / building %s", apartment, building)
    return {"found": False, "apartment": apartment, "building": building}
