"""Tool responsável por sinalizar a classificação da ocorrência ao agente.

A gravação em disco é responsabilidade do nó ``save_occurrence``, que injeta
os campos de contexto do estado (occurrence_id, user_input, reported_by, etc.)
antes de persistir o arquivo JSON.
"""

import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def save_occurrence(
    category: str,
    severity: str,
    summary: str,
    involved_people: list[str],
    apartment: str | None = None,
    building: str | None = None,
) -> dict:
    """Salva a ocorrência de incidente classificada em um arquivo JSON no diretório reports/.

    Deve ser chamada após a classificação do incidente. Recebe apenas os
    campos extraídos pelo modelo — campos de contexto como occurrence_id,
    user_input, reported_by e reported_at são injetados pelo sistema.

    Incidentes com severidade HIGH são adicionalmente salvos em
    reports/escalated/ para triagem prioritária pela equipe de segurança.

    Args:
        category: Categoria do incidente (ACCESS, PACKAGE, NOISE, MAINTENANCE, SECURITY, OTHER).
        severity: Severidade do incidente (LOW, MEDIUM, HIGH).
        summary: Resumo objetivo do incidente em português.
        involved_people: Lista de nomes das pessoas envolvidas.
        apartment: Número do apartamento relacionado ao incidente.
        building: Bloco ou torre relacionado ao incidente.

    Returns:
        Dicionário com os campos classificados confirmando o que foi salvo:
        - ``category``, ``severity``, ``summary``, ``involved_people``,
          ``apartment``, ``building``.
    """
    logger.info(
        "save_occurrence tool called — category: %s, severity: %s", category, severity
    )

    # Retorna apenas os campos classificados; o nó save_occurrence
    # é responsável por injetar os dados de contexto e gravar em disco.
    return {
        "category": category,
        "severity": severity,
        "summary": summary,
        "involved_people": involved_people or [],
        "apartment": apartment,
        "building": building,
    }
