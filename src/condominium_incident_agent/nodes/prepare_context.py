"""Nó responsável por preparar o contexto antes da classificação."""

import logging
from pathlib import Path

from condominium_incident_agent.session import load_session
from condominium_incident_agent.state import AgentState

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "classifier.md"


def _load_prompt_template() -> str:
    """Carrega o template do prompt a partir do arquivo Markdown.

    Returns:
        Conteúdo do arquivo de prompt como string.

    Raises:
        FileNotFoundError: Se o arquivo de prompt não for encontrado.
    """
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _build_session_context() -> str:
    """Constrói o texto de contexto histórico para injeção no prompt.

    Neste ponto do fluxo o apartamento ainda não foi extraído pelo LLM —
    isso só ocorre durante ``classify_incident``. Por isso, o contexto
    pré-injetado exibe o total de ocorrências da sessão sem filtrar por
    apartamento, orientando o LLM a usar a tool ``get_session_history``
    para consultas específicas por unidade.

    Returns:
        Texto informando o total de ocorrências na sessão corrente, ou
        mensagem indicando que a sessão está vazia.
    """
    records = load_session()
    if not records:
        return "Nenhuma ocorrência registrada nesta sessão até o momento."

    total = len(records)
    return (
        f"{total} ocorrência(s) registrada(s) nesta sessão. "
        "Use a tool get_session_history para consultar o histórico "
        "de um apartamento específico e verificar reincidências."
    )


def prepare_context(state: AgentState) -> AgentState:
    """Monta a mensagem de entrada para o LLM e atualiza o histórico.

    Carrega o template do classificador, substitui as variáveis pelo
    conteúdo do estado — incluindo o contexto histórico da sessão —
    e adiciona a mensagem ao ``conversation_history``.

    Args:
        state: Estado atual do agente.

    Returns:
        Estado atualizado com o histórico de conversa preenchido.
    """
    template = _load_prompt_template()

    session_context = _build_session_context()

    prompt = template.replace("{user_input}", state["user_input"])
    prompt = prompt.replace("{reported_by}", state["reported_by"])
    prompt = prompt.replace("{reported_at}", state["reported_at"])
    prompt = prompt.replace("{session_context}", session_context)

    history = list(state.get("conversation_history") or [])
    history.append(prompt)

    logger.info("Context prepared for occurrence_id: %s", state.get("occurrence_id"))

    return {**state, "conversation_history": history}
