"""Testes unitários para o nó prepare_context."""

from unittest.mock import patch

from condominium_incident_agent.nodes.prepare_context import (
    prepare_context,
    _build_session_context,
)


def _make_state(**kwargs) -> dict:
    base = {
        "user_input": "Barulho no corredor",
        "reported_by": "Porteiro Silva",
        "reported_at": "2026-07-14T22:00:00Z",
        "occurrence_id": "test-uuid-001",
        "conversation_history": [],
        "session_history": [],
    }
    base.update(kwargs)
    return base


_FAKE_TEMPLATE = (
    "Relato: {user_input}\n"
    "Reportado por: {reported_by}\n"
    "Data: {reported_at}\n"
    "Contexto: {session_context}"
)


class TestPrepareContext:
    def test_template_variables_substituted(self):
        """Todas as variáveis do template devem ser substituídas corretamente."""
        state = _make_state()
        with (
            patch(
                "condominium_incident_agent.nodes.prepare_context._load_prompt_template",
                return_value=_FAKE_TEMPLATE,
            ),
            patch(
                "condominium_incident_agent.nodes.prepare_context.load_session",
                return_value=[],
            ),
        ):
            result = prepare_context(state)

        history = result["conversation_history"]
        assert len(history) == 1
        prompt = history[0]
        assert "Barulho no corredor" in prompt
        assert "Porteiro Silva" in prompt
        assert "2026-07-14T22:00:00Z" in prompt

    def test_conversation_history_appended(self):
        """O prompt montado deve ser adicionado ao histórico existente."""
        state = _make_state(conversation_history=["mensagem anterior"])
        with (
            patch(
                "condominium_incident_agent.nodes.prepare_context._load_prompt_template",
                return_value=_FAKE_TEMPLATE,
            ),
            patch(
                "condominium_incident_agent.nodes.prepare_context.load_session",
                return_value=[],
            ),
        ):
            result = prepare_context(state)

        assert result["conversation_history"][0] == "mensagem anterior"
        assert len(result["conversation_history"]) == 2

    def test_empty_session_generates_no_occurrences_message(self):
        """Com sessão vazia, o contexto deve informar ausência de ocorrências."""
        state = _make_state()
        with (
            patch(
                "condominium_incident_agent.nodes.prepare_context._load_prompt_template",
                return_value=_FAKE_TEMPLATE,
            ),
            patch(
                "condominium_incident_agent.nodes.prepare_context.load_session",
                return_value=[],
            ),
        ):
            result = prepare_context(state)

        prompt = result["conversation_history"][-1]
        assert "Nenhuma ocorrência" in prompt

    def test_session_with_records_shows_total(self):
        """Com histórico existente, o contexto deve mencionar o total de registros."""
        records = [
            {"occurrence_id": "1", "apartment": "302"},
            {"occurrence_id": "2", "apartment": "401"},
        ]
        state = _make_state()
        with (
            patch(
                "condominium_incident_agent.nodes.prepare_context._load_prompt_template",
                return_value=_FAKE_TEMPLATE,
            ),
            patch(
                "condominium_incident_agent.nodes.prepare_context.load_session",
                return_value=records,
            ),
        ):
            result = prepare_context(state)

        prompt = result["conversation_history"][-1]
        assert "2" in prompt

    def test_original_state_fields_preserved(self):
        """O nó não deve alterar campos do estado além de conversation_history."""
        state = _make_state(occurrence_id="preserve-me")
        with (
            patch(
                "condominium_incident_agent.nodes.prepare_context._load_prompt_template",
                return_value=_FAKE_TEMPLATE,
            ),
            patch(
                "condominium_incident_agent.nodes.prepare_context.load_session",
                return_value=[],
            ),
        ):
            result = prepare_context(state)

        assert result["occurrence_id"] == "preserve-me"
        assert result["user_input"] == "Barulho no corredor"


class TestBuildSessionContext:
    def test_empty_session_returns_no_occurrences_text(self):
        with patch(
            "condominium_incident_agent.nodes.prepare_context.load_session",
            return_value=[],
        ):
            context = _build_session_context()
        assert "Nenhuma ocorrência" in context

    def test_session_with_one_record_returns_count(self):
        with patch(
            "condominium_incident_agent.nodes.prepare_context.load_session",
            return_value=[{"occurrence_id": "1"}],
        ):
            context = _build_session_context()
        assert "1" in context

    def test_session_with_multiple_records_returns_total(self):
        records = [{"occurrence_id": str(i)} for i in range(5)]
        with patch(
            "condominium_incident_agent.nodes.prepare_context.load_session",
            return_value=records,
        ):
            context = _build_session_context()
        assert "5" in context
