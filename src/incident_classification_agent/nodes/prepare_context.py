"""Nó responsável por preparar o contexto antes da classificação."""

import logging
from pathlib import Path

from incident_classification_agent.session import load_session
from incident_classification_agent.state import AgentState

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


def _build_session_context(apartment: str | None, building: str | None) -> str:
    """Constrói o texto de contexto histórico para injeção no prompt.

    Consulta o session.json diretamente (sem passar pelo LLM) para montar
    o contexto antes da classificação. O LLM ainda pode chamar
    get_session_history durante a classificação para consultas adicionais.

    Args:
        apartment: Número do apartamento extraído do estado.
        building: Bloco/torre extraído do estado.

    Returns:
        Texto formatado com o histórico ou mensagem de ausência de histórico.
    """
    if not apartment:
        return (
            "Nenhuma ocorrência anterior registrada para este apartamento nesta sessão."
        )

    records = load_session()
    matches = [
        r
        for r in records
        if r.get("apartment", "").strip().lower() == apartment.strip().lower()
        and (
            building is None
            or r.get("building", "").strip().lower() == (building or "").strip().lower()
        )
    ]

    if not matches:
        return (
            "Nenhuma ocorrência anterior registrada para este apartamento nesta sessão."
        )

    lines = [
        f"{len(matches)} ocorrência(s) anterior(es) para o apartamento {apartment}:"
    ]
    for idx, rec in enumerate(matches, 1):
        lines.append(
            f"  {idx}. [{rec.get('reported_at', 'N/A')}] "
            f"Categoria: {rec.get('category', 'N/A')} | "
            f"Severidade: {rec.get('severity', 'N/A')} | "
            f"Resumo: {rec.get('summary', 'N/A')}"
        )
    return "\n".join(lines)


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

    session_context = _build_session_context(
        state.get("apartment"),
        state.get("building"),
    )

    prompt = template.replace("{user_input}", state["user_input"])
    prompt = prompt.replace("{reported_by}", state["reported_by"])
    prompt = prompt.replace("{reported_at}", state["reported_at"])
    prompt = prompt.replace("{session_context}", session_context)

    history = list(state.get("conversation_history") or [])
    history.append(prompt)

    logger.info("Context prepared for occurrence_id: %s", state.get("occurrence_id"))

    return {**state, "conversation_history": history}
