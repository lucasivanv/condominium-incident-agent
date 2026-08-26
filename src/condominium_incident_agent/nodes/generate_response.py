"""Nó responsável por gerar a resposta final para o usuário."""

import logging

from condominium_incident_agent.enums import Severity
from condominium_incident_agent.state import AgentState

logger = logging.getLogger(__name__)


def _format_success(state: AgentState) -> str:
    """Formata a resposta de sucesso com todos os dados da ocorrência.

    Args:
        state: Estado atual com os campos já preenchidos.

    Returns:
        Mensagem de resposta formatada como string.
    """
    category = state.get("category")
    severity = state.get("severity")
    category_str = category.value if hasattr(category, "value") else str(category) if category else "N/A"
    severity_str = severity.value if hasattr(severity, "value") else str(severity) if severity else "N/A"

    lines = [
        "✅ Ocorrência registrada com sucesso.",
        "",
        f"🆔 ID: {state.get('occurrence_id', 'N/A')}",
        f"📁 Categoria: {category_str}",
        f"⚠️  Severidade: {severity_str}",
    ]

    if state.get("apartment"):
        lines.append(f"🏠 Apartamento: {state['apartment']}")

    if state.get("building"):
        lines.append(f"🏢 Bloco: {state['building']}")

    if state.get("involved_people"):
        people = ", ".join(state["involved_people"])
        lines.append(f"👥 Envolvidos: {people}")

    resident = state.get("resident_info")
    if resident and resident.get("found"):
        lines.append(f"🔍 Morador cadastrado: {resident.get('resident_name', 'N/A')}")
        visitors = resident.get("authorized_visitors") or []
        if visitors:
            lines.append(f"   Visitantes autorizados: {', '.join(visitors)}")

    if state.get("summary"):
        lines.append("")
        lines.append(f"📝 Resumo: {state['summary']}")

    if state.get("output_file"):
        lines.append("")
        lines.append(f"💾 Arquivo salvo em: {state['output_file']}")

    if state.get("escalated_file"):
        lines.append(f"🚨 ESCALONADO (HIGH): {state['escalated_file']}")

    if state.get("flowise_delivery_status"):
        lines.append(f"🔗 Flowise: {state['flowise_delivery_status']}")
    if state.get("flowise_action"):
        lines.append(f"🎯 Ação operacional: {state['flowise_action']}")
    triage = state.get("flowise_triage") or {}
    if triage.get("responsible_team"):
        lines.append(f"👷 Equipe responsável: {triage['responsible_team']}")
    if triage.get("priority"):
        lines.append(f"📌 Prioridade operacional: {triage['priority']}")
    if triage.get("sla_minutes") is not None:
        lines.append(f"⏱️ Prazo de atendimento: {triage['sla_minutes']} min")
    if triage.get("diagnostic_summary"):
        lines.append(f"📊 Diagnóstico Flowise: {triage['diagnostic_summary']}")

    return "\n".join(lines)


def _format_error(state: AgentState) -> str:
    """Formata a resposta de falha quando a classificação não foi possível.

    Args:
        state: Estado atual com ``classification_error`` preenchido.

    Returns:
        Mensagem de erro formatada como string.
    """
    lines = [
        "❌ A ocorrência não foi registrada.",
        "",
        f"🆔 ID: {state.get('occurrence_id', 'N/A')}",
        f"📋 Relato recebido: {state.get('user_input', '')}",
        "",
        f"⚠️  Motivo: {state.get('classification_error', 'Erro desconhecido')}",
        "",
        "Por favor, verifique o motivo e tente novamente.",
    ]
    if state.get("severity") == Severity.HIGH and state.get("classification_error", "").startswith(
        "Ação crítica bloqueada"
    ):
        lines[0] = "🛑 Ocorrência classificada, mas bloqueada por segurança."
        lines[-1] = "Forneça uma aprovação humana externa válida para prosseguir."
    return "\n".join(lines)


def _format_multiple_incidents(state: AgentState) -> str:
    """Formata a mensagem de rejeição por múltiplos incidentes detectados.

    Args:
        state: Estado atual com ``multiple_incidents_detected`` marcado.

    Returns:
        Mensagem orientando o usuário a submeter um relato por vez.
    """
    lines = [
        "⚠️  Múltiplos incidentes detectados no relato.",
        "",
        "Este sistema aceita apenas um incidente por vez para garantir",
        "rastreabilidade e classificação precisa de cada ocorrência.",
        "",
        f"🆔 ID gerado: {state.get('occurrence_id', 'N/A')}",
        "",
        "Por favor, divida o relato e submeta cada incidente separadamente.",
    ]
    return "\n".join(lines)


def generate_response(state: AgentState) -> AgentState:
    """Gera a resposta final e a adiciona ao histórico de conversa.

    Exibe uma resposta de sucesso se a classificação foi concluída, ou
    uma resposta de erro se ``classification_error`` estiver preenchido.

    Args:
        state: Estado atual com todos os campos processados.

    Returns:
        Estado atualizado com a resposta final no ``conversation_history``.
    """
    if state.get("multiple_incidents_detected"):
        response = _format_multiple_incidents(state)
    elif state.get("classification_error"):
        response = _format_error(state)
    else:
        response = _format_success(state)

    history = list(state.get("conversation_history") or [])
    history.append(response)

    logger.info("Response generated for occurrence_id: %s", state.get("occurrence_id"))

    print(response)

    return {**state, "conversation_history": history}
