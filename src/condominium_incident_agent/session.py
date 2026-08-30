"""Módulo centralizado para persistência e consulta do histórico de sessão.

SESSION_FILE, load_session e append_to_session são importados por:
- tools/get_session_history.py
- nodes/prepare_context.py
- nodes/save_occurrence.py

Centralizar aqui evita duplicação de caminhos e acoplamento via APIs internas.

Constantes de contexto
----------------------
RECENT_CONTEXT_LIMIT : int
    Número máximo de ocorrências recentes retornadas por consulta de
    histórico. Limita o volume de contexto injetado no prompt do LLM,
    evitando estouro de janela de contexto em sessões longas.
    Aplicado em ``tools/get_session_history`` e ``nodes/prepare_context``.

CONVERSATION_HISTORY_LIMIT : int
    Número máximo de entradas mantidas em ``AgentState.conversation_history``.
    Garante que o histórico de conversa não cresça indefinidamente no
    checkpointer — apenas as N entradas mais recentes são preservadas.
"""

import json
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).parent.parent.parent
SESSION_FILE = _BASE_DIR / "reports" / "session.json"

# Limite de ocorrências retornadas por consulta de histórico de apartamento.
# Valor conservador para caber em qualquer janela de contexto de LLM pequeno
# (e.g. Ollama local com 4 k tokens de contexto).
RECENT_CONTEXT_LIMIT: int = 10

# Limite de entradas em conversation_history mantidas entre invocações.
# Preserva prompt + resposta da invocação atual mais as N-1 anteriores.
CONVERSATION_HISTORY_LIMIT: int = 6


def _normalize_filter_value(value: object) -> str:
    """Normaliza valores opcionais usados nos filtros do histórico."""
    return str(value).strip().lower() if value is not None else ""


def find_session_records(
    records: list[dict], apartment: str, building: str | None = None
) -> list[dict]:
    """Retorna registros do apartamento e, opcionalmente, do bloco informado."""
    apartment_key = _normalize_filter_value(apartment)
    building_key = _normalize_filter_value(building) if building is not None else None

    return [
        record
        for record in records
        if _normalize_filter_value(record.get("apartment")) == apartment_key
        and (
            building_key is None
            or _normalize_filter_value(record.get("building")) == building_key
        )
    ]


def load_session() -> list[dict]:
    """Carrega o histórico de sessão do arquivo local.

    Returns:
        Lista de ocorrências registradas na sessão. Vazia se o arquivo
        não existir ou estiver corrompido.
    """
    if not SESSION_FILE.exists():
        return []
    try:
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            logger.warning("session.json has unexpected format; treating as empty.")
            return []
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load session.json: %s", exc)
        return []


def append_to_session(entry: dict) -> None:
    """Adiciona uma entrada ao arquivo de sessão de forma segura.

    Utiliza escrita atômica via arquivo temporário no mesmo diretório:
    o conteúdo é escrito num arquivo ``.tmp`` e depois renomeado sobre
    o destino final. No Windows, onde ``os.replace`` é garantido atômico
    pelo sistema de arquivos NTFS, isso evita truncamentos parciais em
    caso de interrupção entre escrita e fechamento.

    Chamadas concorrentes de processos distintos ainda podem sobrescrever
    umas às outras — para o escopo deste projeto isso é aceitável, pois
    ocorrências são processadas sequencialmente num único processo.

    Args:
        entry: Dicionário com os dados da ocorrência a ser adicionada.
    """
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)

    records = load_session()
    records.append(entry)

    content = json.dumps(records, ensure_ascii=False, indent=2)

    # Escreve em arquivo temporário no mesmo diretório para garantir que
    # o rename seja atômico (ambos no mesmo volume de disco).
    fd, tmp_path = tempfile.mkstemp(
        dir=SESSION_FILE.parent,
        prefix=".session_tmp_",
        suffix=".json",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp_path, SESSION_FILE)
    except Exception:
        # Garante que o arquivo temporário seja removido em caso de falha.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    logger.info("Session updated — total records: %d", len(records))
