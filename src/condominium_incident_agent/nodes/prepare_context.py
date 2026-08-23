"""Nó responsável por preparar o contexto antes da classificação."""

import logging
import re
from pathlib import Path

from condominium_incident_agent.session import (
    CONVERSATION_HISTORY_LIMIT,
    RECENT_CONTEXT_LIMIT,
    find_session_records,
    load_session,
)
from condominium_incident_agent.state import AgentState

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "classifier.md"

# Padrão simples para extrair número de apartamento do texto do relato.
# Exemplos reconhecidos: "apartamento 302", "apto 12", "apt. 7", "ap 501".
# Propositalmente permissivo — falsos positivos são inofensivos porque o
# LLM descarta contexto irrelevante. Falsos negativos significam apenas
# que o contexto granular não é pré-injetado (o LLM ainda pode usar a tool).
_APARTMENT_RE = re.compile(
    r"\b(?:apartamento|apto\.?|apt\.?|ap\.?)\s+(\w+)",
    re.IGNORECASE,
)


def _load_prompt_template() -> str:
    """Carrega o template do prompt a partir do arquivo Markdown.

    Returns:
        Conteúdo do arquivo de prompt como string.

    Raises:
        FileNotFoundError: Se o arquivo de prompt não for encontrado.
    """
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _extract_apartment_hint(text: str) -> str | None:
    """Tenta extrair o número de apartamento mencionado no relato.

    Usado para enriquecer o contexto pré-injetado com ocorrências
    específicas desse apartamento, reduzindo a necessidade de tool calls
    em casos simples e orientando melhor o raciocínio do LLM.

    Args:
        text: Texto bruto do relato.

    Returns:
        Número do apartamento como string, ou None se não encontrado.
    """
    match = _APARTMENT_RE.search(text)
    return match.group(1) if match else None


def _build_session_context(
    user_input: str = "", records: list[dict] | None = None
) -> str:
    """Constrói o texto de contexto histórico para injeção no prompt.

    Estratégia em dois níveis:

    1. **Contexto granular**: quando o apartamento pode ser inferido do
       relato *antes* da classificação, injeta as ocorrências mais recentes
       desse apartamento (limitadas a ``RECENT_CONTEXT_LIMIT``). Isso
       permite que o LLM raciocine sobre reincidência sem precisar emitir
       um tool call — ou pelo menos com mais informação no primeiro turno.

    2. **Contexto agregado**: quando o apartamento não pode ser inferido,
       injeta apenas o total de ocorrências da sessão e instrui o LLM a
       usar ``get_session_history`` para consultas específicas.

    Em ambos os casos o contexto é limitado para não estourar a janela
    de contexto do modelo.

    Args:
        user_input: Texto bruto do relato. Usado para tentar extrair o
            apartamento antecipadamente.
        records: Snapshot de ocorrências disponível no estado. Quando
            omitido, carrega a sessão persistida para compatibilidade direta.

    Returns:
        Texto de contexto pronto para substituição no template.
    """
    if records is None:
        records = load_session()

    if not records:
        return "Nenhuma ocorrência registrada nesta sessão até o momento."

    total = len(records)
    apt_hint = _extract_apartment_hint(user_input)

    if apt_hint:
        # Filtra ocorrências do apartamento mencionado (sem filtro de bloco
        # neste ponto — o LLM confirmará via tool se necessário).
        apt_matches = find_session_records(records, apt_hint)

        if apt_matches:
            # Limita ao contexto mais recente para não encher o prompt.
            recent = apt_matches[-RECENT_CONTEXT_LIMIT:]
            lines = [
                f"{total} ocorrência(s) registrada(s) nesta sessão.",
                (
                    f"Ocorrências anteriores para o apartamento {apt_hint} "
                    f"({len(recent)} de {len(apt_matches)} exibidas):"
                ),
            ]
            for occ in recent:
                lines.append(
                    f"  - [{occ.get('reported_at', '?')}] "
                    f"categoria={occ.get('category', '?')} "
                    f"severidade={occ.get('severity', '?')}: "
                    f"{occ.get('summary', '')}"
                )
            lines.append(
                "Use a tool get_session_history para confirmar ou refinar "
                "estas informações — em caso de divergência, o retorno da "
                "tool tem precedência."
            )
            return "\n".join(lines)

    # Fallback: contexto agregado sem detalhes por apartamento.
    return (
        f"{total} ocorrência(s) registrada(s) nesta sessão. "
        "Use a tool get_session_history para consultar o histórico "
        "de um apartamento específico e verificar reincidências."
    )


def _cap_conversation_history(history: list[str]) -> list[str]:
    """Retorna as últimas N entradas do histórico de conversa.

    Impede crescimento ilimitado do ``conversation_history`` no
    checkpointer (MemorySaver) entre invocações do mesmo thread_id.
    Mantém apenas as ``CONVERSATION_HISTORY_LIMIT`` entradas mais recentes.

    Args:
        history: Lista atual de entradas do histórico.

    Returns:
        Lista truncada com no máximo ``CONVERSATION_HISTORY_LIMIT`` entradas.
    """
    if len(history) <= CONVERSATION_HISTORY_LIMIT:
        return history
    truncated = history[-CONVERSATION_HISTORY_LIMIT:]
    logger.debug(
        "conversation_history truncated: %d → %d entries",
        len(history),
        len(truncated),
    )
    return truncated


def prepare_context(state: AgentState) -> AgentState:
    """Monta a mensagem de entrada para o LLM e atualiza o histórico.

    Carrega o template do classificador, substitui as variáveis pelo
    conteúdo do estado — incluindo o contexto histórico da sessão —
    e adiciona a mensagem ao ``conversation_history``.

    O ``conversation_history`` é truncado a ``CONVERSATION_HISTORY_LIMIT``
    entradas antes da adição para evitar crescimento ilimitado entre
    invocações preservadas pelo checkpointer.

    Args:
        state: Estado atual do agente.

    Returns:
        Estado atualizado com o histórico de conversa preenchido.
    """
    template = _load_prompt_template()

    session_context = _build_session_context(
        state.get("user_input", ""), state.get("session_history")
    )

    prompt = template.replace("{user_input}", state["user_input"])
    prompt = prompt.replace("{reported_by}", state["reported_by"])
    prompt = prompt.replace("{reported_at}", state["reported_at"])
    prompt = prompt.replace("{session_context}", session_context)

    history = _cap_conversation_history(list(state.get("conversation_history") or []))
    history.append(prompt)

    logger.info("Context prepared for occurrence_id: %s", state.get("occurrence_id"))

    return {**state, "conversation_history": history}
