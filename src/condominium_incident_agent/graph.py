"""Definição e compilação do grafo LangGraph do agente."""

import logging

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from condominium_incident_agent.nodes.classify_incident import (
    _route_after_classify,
    classify_incident,
)
from condominium_incident_agent.nodes.generate_response import generate_response
from condominium_incident_agent.nodes.handle_error import handle_error
from condominium_incident_agent.nodes.prepare_context import (
    prepare_context,
    retrieve_conversation_context,
    retrieve_session_context,
)
from condominium_incident_agent.nodes.save_occurrence import save_occurrence
from condominium_incident_agent.nodes.validate_input import (
    _route_after_validate,
    validate_input,
)
from condominium_incident_agent.observability import instrument_node
from condominium_incident_agent.state import AgentState

logger = logging.getLogger(__name__)


def _route_after_validate_fanout(state: AgentState) -> str | list[str]:
    """Expande o caminho normal para as duas recuperações independentes."""
    route = _route_after_validate(state)
    if route == "prepare_context":
        return ["retrieve_session_context", "retrieve_conversation_context"]
    return route


def build_graph() -> StateGraph:
    """Constrói e compila o grafo de processamento de incidentes.

    Utiliza MemorySaver como checkpointer para preservar o estado completo
    do agente entre execuções do mesmo thread_id. Isso permite que variáveis
    de estado — incluindo session_history — sejam mantidas em memória durante
    toda a vida do processo, sem depender apenas do session.json em disco.

    Nota: MemorySaver é volátil — o estado é perdido quando o processo encerra.
    Para persistência entre processos distintos, o session.json (atualizado
    pelo nó save_occurrence) serve como fonte de verdade durável.

    Fluxo principal:
         START → validate_input → [retrieve_session_context,
             retrieve_conversation_context] → prepare_context → classify_incident
               → (condicional) → save_occurrence → generate_response → END

    Fluxo de múltiplos incidentes (rejeição antecipada):
        validate_input → generate_response → END

    Fluxo de erro de classificação:
        classify_incident → handle_error → generate_response → END

    Returns:
        Grafo compilado pronto para execução.
    """
    graph = StateGraph(AgentState)

    graph.add_node("validate_input", instrument_node("validate_input", validate_input))
    graph.add_node(
        "retrieve_session_context",
        instrument_node("retrieve_session_context", retrieve_session_context),
    )
    graph.add_node(
        "retrieve_conversation_context",
        instrument_node("retrieve_conversation_context", retrieve_conversation_context),
    )
    graph.add_node("prepare_context", instrument_node("prepare_context", prepare_context))
    graph.add_node("classify_incident", instrument_node("classify_incident", classify_incident))
    graph.add_node("handle_error", instrument_node("handle_error", handle_error))
    graph.add_node("save_occurrence", instrument_node("save_occurrence", save_occurrence))
    graph.add_node("generate_response", instrument_node("generate_response", generate_response))

    graph.add_edge(START, "validate_input")

    graph.add_conditional_edges(
        "validate_input",
        _route_after_validate_fanout,
        {
            "retrieve_session_context": "retrieve_session_context",
            "retrieve_conversation_context": "retrieve_conversation_context",
            "generate_response": "generate_response",
        },
    )

    graph.add_edge("retrieve_session_context", "prepare_context")
    graph.add_edge("retrieve_conversation_context", "prepare_context")
    graph.add_edge("prepare_context", "classify_incident")

    graph.add_conditional_edges(
        "classify_incident",
        _route_after_classify,
        {
            "save_occurrence": "save_occurrence",
            "handle_error": "handle_error",
        },
    )

    graph.add_edge("handle_error", "generate_response")
    graph.add_edge("save_occurrence", "generate_response")
    graph.add_edge("generate_response", END)

    checkpointer = MemorySaver()
    compiled = graph.compile(checkpointer=checkpointer)

    logger.info("Graph compiled successfully with MemorySaver checkpointer.")

    return compiled
