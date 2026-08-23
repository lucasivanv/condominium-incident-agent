"""Testes unitários para o nó handle_error."""

from condominium_incident_agent.nodes.handle_error import handle_error


def _make_state(**kwargs) -> dict:
    base = {
        "occurrence_id": "test-uuid-001",
        "user_input": "Barulho no corredor",
        "reported_by": "Porteiro Silva",
        "reported_at": "2026-07-14T22:00:00Z",
        "classification_error": None,
        "category": None,
        "severity": None,
        "conversation_history": [],
        "session_history": [],
    }
    base.update(kwargs)
    return base


class TestHandleError:
    def test_returns_state_unchanged_with_error(self):
        """Estado com erro deve ser retornado sem modificações."""
        state = _make_state(
            classification_error="Campo 'category' ausente na resposta do LLM."
        )
        result = handle_error(state)

        assert result is state
        assert result["classification_error"] == "Campo 'category' ausente na resposta do LLM."

    def test_returns_state_unchanged_without_error(self):
        """Estado sem erro também deve ser retornado sem modificações."""
        state = _make_state(classification_error=None)
        result = handle_error(state)

        assert result is state
        assert result["classification_error"] is None

    def test_does_not_modify_occurrence_id(self):
        """O nó não deve alterar o occurrence_id."""
        state = _make_state(
            occurrence_id="preserve-this-id",
            classification_error="erro qualquer",
        )
        result = handle_error(state)
        assert result["occurrence_id"] == "preserve-this-id"

    def test_does_not_modify_user_input(self):
        """O nó não deve alterar o user_input."""
        state = _make_state(
            user_input="Relato original intacto",
            classification_error="erro",
        )
        result = handle_error(state)
        assert result["user_input"] == "Relato original intacto"

    def test_handles_unknown_error_gracefully(self):
        """Quando classification_error não está no estado, não deve lançar exceção."""
        state = {}
        result = handle_error(state)
        assert result is state
