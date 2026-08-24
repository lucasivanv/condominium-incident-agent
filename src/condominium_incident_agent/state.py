"""Definição do estado compartilhado entre os nós do grafo."""

from typing import TypedDict

from condominium_incident_agent.enums import Category, Severity


class AgentState(TypedDict):
    """Estado completo do agente durante o processamento de um incidente.

    Attributes:
        user_input: Texto bruto informado pelo usuário.
        reported_by: Nome de quem reportou o incidente.
        reported_at: Data/hora do reporte (ISO 8601).
        occurrence_id: Identificador único gerado para a ocorrência.
        category: Categoria classificada do incidente.
        severity: Severidade classificada do incidente.
        involved_people: Lista de pessoas envolvidas no incidente.
        apartment: Apartamento relacionado ao incidente.
        building: Bloco/torre relacionado ao incidente.
        summary: Resumo gerado pelo agente em português.
        conversation_history: Histórico de mensagens da conversa.
        output_file: Caminho do arquivo JSON salvo com a ocorrência.
        escalated_file: Caminho do arquivo de escalonamento (apenas para HIGH).
        classification_error: Mensagem de erro caso a classificação falhe.
        resident_info: Informações do morador consultado via tool.
        multiple_incidents_detected: True se o relato contém mais de um
            incidente distinto, sinalizando rejeição do input.
        session_history: Histórico acumulado de ocorrências processadas na
            sessão corrente. Cada entrada representa uma ocorrência já
            classificada com sucesso, contendo os campos relevantes para
            consulta de reincidência e contexto entre interações.
        session_context: Contexto textual recuperado do histórico persistido.
        conversation_context: Histórico conversacional limitado para o prompt.
        human_approval: Aprovação externa assinada para ações críticas.
    """

    user_input: str
    reported_by: str
    reported_at: str
    occurrence_id: str | None
    category: Category | None
    severity: Severity | None
    involved_people: list[str]
    apartment: str | None
    building: str | None
    summary: str | None
    conversation_history: list[str]
    output_file: str | None
    escalated_file: str | None
    classification_error: str | None
    resident_info: dict | None
    multiple_incidents_detected: bool | None
    session_history: list[dict]
    session_context: str | None
    conversation_context: list[str] | None
    human_approval: dict | None
    correlation_id: str
