"""Módulo centralizado para persistência e consulta do histórico de sessão.

SESSION_FILE, load_session e append_to_session são importados por:
- tools/get_session_history.py
- nodes/prepare_context.py
- nodes/save_occurrence.py

Centralizar aqui evita duplicação de caminhos e acoplamento via APIs internas.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).parent.parent.parent
SESSION_FILE = _BASE_DIR / "reports" / "session.json"


def load_session() -> list[dict]:
    """Carrega o histórico de sessão do arquivo local.

    Returns:
        Lista de ocorrências registradas na sessão. Vazia se o arquivo
        não existir ou estiver corrompido.
    """
    if not SESSION_FILE.exists():
        return []
    try:
        return json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load session.json: %s", exc)
        return []


def append_to_session(entry: dict) -> None:
    """Adiciona uma entrada ao arquivo de sessão.

    Realiza leitura-modificação-escrita do arquivo JSON. Não há garantia
    de atomicidade real — em caso de interrupção entre a leitura e a
    escrita, a entrada pode ser perdida. Para o escopo do projeto essa
    abordagem é suficiente.

    Args:
        entry: Dicionário com os dados da ocorrência a ser adicionada.
    """
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)

    records = load_session()
    # Se load_session retornou lista vazia por corrupção, reinicia o arquivo
    if not isinstance(records, list):
        records = []

    records.append(entry)
    SESSION_FILE.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("Session updated — total records: %d", len(records))
