"""Schema de validação do input do usuário via Pydantic.

Define o contrato de entrada do agente: quais campos o usuário deve
fornecer, quais são obrigatórios, quais têm defaults e quais as regras
de validação aplicadas antes do processamento.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator


class IncidentInput(BaseModel):
    """Dados de entrada fornecidos pelo usuário para registro de um incidente.

    Apenas os campos relevantes para o usuário são expostos aqui.
    Campos internos do agente (category, severity, occurrence_id, etc.)
    são gerados durante o processamento e não fazem parte deste contrato.

    Attributes:
        user_input: Relato textual do incidente. Obrigatório e não pode
            ser vazio após remoção de espaços.
        reported_by: Nome de quem está reportando o incidente. Obrigatório.
        reported_at: Data e hora do ocorrido em formato ISO 8601.
            Se não informado, assume o momento atual em UTC.
    """

    user_input: str = Field(
        ...,
        min_length=1,
        description="Relato textual do incidente. Não pode ser vazio.",
    )
    reported_by: str = Field(
        ...,
        min_length=1,
        description="Nome de quem está reportando o incidente.",
    )
    reported_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="Data e hora do incidente em ISO 8601. Default: momento atual em UTC.",
    )

    @field_validator("user_input", "reported_by", mode="before")
    @classmethod
    def reject_blank_strings(cls, value: object) -> object:
        """Rejeita strings compostas apenas por espaços em branco."""
        if isinstance(value, str) and not value.strip():
            raise ValueError("O campo não pode ser vazio ou conter apenas espaços.")
        return value

    @field_validator("reported_at", mode="before")
    @classmethod
    def parse_reported_at(cls, value: object) -> object:
        """Aceita strings ISO 8601 com ou sem sufixo 'Z'.

        Strings como '2026-07-14T22:18:42Z' são normalizadas para
        datetime com timezone UTC antes da validação padrão do Pydantic.
        """
        if isinstance(value, str):
            return value.replace("Z", "+00:00")
        return value

    def to_initial_state(self) -> dict:
        """Converte o input validado no estado inicial do agente.

        Preenche todos os campos do AgentState com seus valores iniciais,
        deixando os campos de saída do agente como None ou listas vazias.

        Returns:
            Dicionário compatível com AgentState pronto para invocar o grafo.
        """
        return {
            "user_input": self.user_input.strip(),
            "reported_by": self.reported_by.strip(),
            "reported_at": self.reported_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "occurrence_id": None,
            "category": None,
            "severity": None,
            "involved_people": [],
            "apartment": None,
            "building": None,
            "summary": None,
            "conversation_history": [],
            "output_file": None,
            "escalated_file": None,
            "classification_error": None,
            "resident_info": None,
            "multiple_incidents_detected": None,
            "session_history": [],
        }
