"""Nó responsável por classificar o incidente via LLM com uso de tools."""

import json
import logging

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.prebuilt import ToolNode

from condominium_incident_agent.enums import Category, Severity
from condominium_incident_agent.llm import get_llm, with_llm_retry
from condominium_incident_agent.security import (
    authorize_tool_call,
    sanitize_untrusted_data,
    sanitize_untrusted_text,
)
from condominium_incident_agent.state import AgentState
from condominium_incident_agent.tools.get_session_history import get_session_history
from condominium_incident_agent.tools.lookup_resident import lookup_resident

logger = logging.getLogger(__name__)

TOOLS = [lookup_resident, get_session_history]
tool_node = ToolNode(TOOLS)


def _extract_json(text: str) -> dict:
    """Extrai o primeiro bloco JSON encontrado na resposta do LLM.

    Tenta parsear a partir de cada '{' encontrado no texto usando
    JSONDecoder.raw_decode, evitando capturas incorretas por regex greedy.

    Args:
        text: Texto retornado pelo modelo.

    Returns:
        Dicionário com os dados extraídos.

    Raises:
        ValueError: Se nenhum JSON válido for encontrado.
    """
    decoder = json.JSONDecoder()
    for i, char in enumerate(text):
        if char == "{":
            try:
                obj, _ = decoder.raw_decode(text, i)
                return obj
            except json.JSONDecodeError:
                continue
    raise ValueError("Nenhum JSON válido encontrado na resposta do LLM.")


def _route_after_classify(state: AgentState) -> str:
    """Decide o próximo nó após a classificação.

    Roteia para ``handle_error`` se a classificação falhou (campos
    obrigatórios ausentes ou inválidos). Caso contrário, segue para
    ``save_occurrence``.

    Args:
        state: Estado atual após a execução de ``classify_incident``.

    Returns:
        Nome do próximo nó: ``"save_occurrence"`` ou ``"handle_error"``.
    """
    if state.get("classification_error"):
        logger.warning("Routing to handle_error — reason: %s", state["classification_error"])
        return "handle_error"
    return "save_occurrence"


def classify_incident(state: AgentState) -> AgentState:
    """Envia o prompt ao LLM com tools disponíveis e extrai a classificação.

    O LLM recebe as tools ``lookup_resident`` e ``get_session_history`` via
    ``bind_tools``. Quando o modelo emite tool calls, elas são executadas
    pelo ``ToolNode`` e o resultado é repassado de volta ao LLM para que
    ele incorpore as informações antes de produzir a classificação final.

    Campos atualizados no estado: ``category``, ``severity``,
    ``involved_people``, ``apartment``, ``building``, ``summary``,
    ``resident_info``, ``output_file``, ``escalated_file``,
    ``conversation_history`` e ``classification_error``.

    Args:
        state: Estado atual do agente (requer ``conversation_history`` preenchido).

    Returns:
        Estado atualizado com os campos de classificação preenchidos.
    """
    history = state.get("conversation_history") or []
    prompt_text = history[-1] if history else state["user_input"]

    llm = get_llm()
    llm_with_tools = with_llm_retry(llm.bind_tools(TOOLS))

    messages = [HumanMessage(content=prompt_text)]
    resident_info: dict | None = None
    ai_message: AIMessage | None = None

    # Agentic loop: continua enquanto o LLM emitir tool calls
    try:
        for iteration in range(5):  # limite de segurança para evitar loop infinito
            ai_message = llm_with_tools.invoke(messages)
            messages.append(ai_message)

            if not ai_message.tool_calls:
                break

            # Tools locais são determinísticas; falha vira erro controlado,
            # sem repetir operações que podem ter efeitos colaterais.
            for tool_call in ai_message.tool_calls:
                authorize_tool_call(tool_call["name"], tool_call.get("args", {}))
            tool_results = tool_node.invoke({"messages": messages})
            tool_messages: list[ToolMessage] = tool_results["messages"]

            for tm in tool_messages:
                raw_tool_content = tm.content
                try:
                    result = (
                        json.loads(raw_tool_content)
                        if isinstance(raw_tool_content, str)
                        else raw_tool_content
                    )
                except (json.JSONDecodeError, TypeError):
                    result = raw_tool_content

                safe_result = sanitize_untrusted_data(result)
                safe_content = (
                    json.dumps(safe_result, ensure_ascii=False)
                    if not isinstance(safe_result, str)
                    else safe_result
                )
                messages.append(
                    ToolMessage(
                        content=safe_content,
                        tool_call_id=tm.tool_call_id,
                        name=tm.name,
                    )
                )

                tool_name = tm.name if hasattr(tm, "name") else ""
                if tool_name == "lookup_resident":
                    resident_info = safe_result if isinstance(safe_result, dict) and safe_result.get("found") else None
        else:
            raise RuntimeError("Limite de chamadas de tools atingido sem resposta final.")
    except Exception as exc:
        error = f"Falha na dependência externa durante a classificação: {type(exc).__name__}."
        logger.exception("Classification dependency failed for %s", state.get("occurrence_id"))
        return {
            **state,
            "category": None,
            "severity": None,
            "resident_info": resident_info,
            "classification_error": error,
        }

    raw = ai_message.content
    logger.debug(
        "LLM final response received — occurrence_id: %s, characters: %d",
        state.get("occurrence_id"),
        len(raw),
    )

    # Atualiza histórico com a resposta final do LLM
    history = list(history)
    history.append(sanitize_untrusted_text(raw))

    # Valida e extrai a classificação do JSON retornado pelo LLM
    classification_error: str | None = None
    category: Category | None = None
    severity: Severity | None = None
    data: dict = {}

    try:
        data = _extract_json(raw)

        raw_category = data.get("category")
        raw_severity = data.get("severity")

        if not raw_category:
            raise ValueError("Campo 'category' ausente na resposta do LLM.")
        if not raw_severity:
            raise ValueError("Campo 'severity' ausente na resposta do LLM.")

        category = Category(raw_category)
        severity = Severity(raw_severity)

        # Loga o raciocínio de severidade quando disponível
        reasoning = data.get("reasoning")
        if reasoning:
            logger.info(
                "Severity reasoning — base: %s | recurrence: %s (%s) | final: %s",
                reasoning.get("base_severity"),
                reasoning.get("recurrence_detected"),
                reasoning.get("recurrence_count"),
                reasoning.get("final_severity"),
            )

    except (ValueError, KeyError) as exc:
        classification_error = str(exc)
        logger.error("Classification failed — error_type: %s", type(exc).__name__)

    if not classification_error:
        logger.info(
            "Incident classified — category: %s, severity: %s, occurrence_id: %s",
            category,
            severity,
            state.get("occurrence_id"),
        )

    return {
        **state,
        "category": category,
        "severity": severity,
        "involved_people": data.get("involved_people") or [],
        "apartment": data.get("apartment"),
        "building": data.get("building"),
        "summary": data.get("summary"),
        "resident_info": resident_info,
        "conversation_history": history,
        "classification_error": classification_error,
    }
