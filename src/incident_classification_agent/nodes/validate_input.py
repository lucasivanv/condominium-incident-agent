"""Nó responsável por validar os dados de entrada do agente."""

import logging
import uuid
from datetime import UTC, datetime

from langchain_core.messages import HumanMessage

from incident_classification_agent.llm import get_llm
from incident_classification_agent.state import AgentState

logger = logging.getLogger(__name__)

_DETECTION_PROMPT = """\
Você é um analisador de texto objetivo. Leia o relato abaixo e determine se ele descreve \
UM único incidente ou MÚLTIPLOS incidentes distintos (eventos independentes, envolvendo \
pessoas, locais ou situações diferentes).

Responda APENAS com uma das palavras: SINGLE ou MULTIPLE

Relato:
{user_input}
"""


def _detect_multiple_incidents(user_input: str) -> bool:
    """Consulta o LLM para verificar se o relato contém múltiplos incidentes.

    Args:
        user_input: Texto do relato a ser analisado.

    Returns:
        True se múltiplos incidentes forem detectados, False caso contrário.
    """
    llm = get_llm()
    prompt = _DETECTION_PROMPT.format(user_input=user_input)
    response = llm.invoke([HumanMessage(content=prompt)])
    answer = response.content.strip().upper()

    logger.info("Multiple incidents detection result: %s", answer)

    return "MULTIPLE" in answer


def _route_after_validate(state: AgentState) -> str:
    """Decide o próximo nó após a validação da entrada.

    Se múltiplos incidentes foram detectados, encerra o fluxo antecipadamente
    em ``generate_response`` para informar o usuário. Caso contrário, segue
    o fluxo normal para ``prepare_context``.

    Args:
        state: Estado atual após a execução de ``validate_input``.

    Returns:
        Nome do próximo nó: ``"prepare_context"`` ou ``"generate_response"``.
    """
    if state.get("multiple_incidents_detected"):
        logger.warning(
            "Multiple incidents detected — short-circuiting to generate_response."
        )
        return "generate_response"
    return "prepare_context"


def validate_input(state: AgentState) -> AgentState:
    """Valida e normaliza os campos obrigatórios do estado de entrada.

    Garante que ``user_input`` e ``reported_by`` estejam presentes.
    Preenche ``reported_at`` com o instante atual quando ausente.
    Gera um ``occurrence_id`` único para rastrear a ocorrência.
    Detecta se o relato contém múltiplos incidentes distintos via LLM —
    nesse caso, ``multiple_incidents_detected`` é marcado como True e o
    fluxo é encerrado antes da classificação.

    Args:
        state: Estado atual do agente.

    Returns:
        Estado atualizado com os campos validados e normalizados.

    Raises:
        ValueError: Se ``user_input`` ou ``reported_by`` estiverem vazios.
    """
    user_input = (state.get("user_input") or "").strip()
    reported_by = (state.get("reported_by") or "").strip()

    if not user_input:
        raise ValueError("O campo 'user_input' é obrigatório.")

    if not reported_by:
        raise ValueError("O campo 'reported_by' é obrigatório.")

    reported_at = state.get("reported_at") or datetime.now(tz=UTC).isoformat()
    occurrence_id = state.get("occurrence_id") or str(uuid.uuid4())

    multiple_incidents_detected = _detect_multiple_incidents(user_input)

    logger.info(
        "Input validated — occurrence_id: %s | multiple_incidents: %s",
        occurrence_id,
        multiple_incidents_detected,
    )

    return {
        **state,
        "user_input": user_input,
        "reported_by": reported_by,
        "reported_at": reported_at,
        "occurrence_id": occurrence_id,
        "involved_people": state.get("involved_people") or [],
        "conversation_history": state.get("conversation_history") or [],
        "multiple_incidents_detected": multiple_incidents_detected,
    }
