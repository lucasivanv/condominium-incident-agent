"""Testes unitários para o nó prepare_context."""

from unittest.mock import patch

from condominium_incident_agent.nodes.prepare_context import (
    _build_session_context,
    _cap_conversation_history,
    _extract_apartment_hint,
    prepare_context,
)
from condominium_incident_agent.session import (
    CONVERSATION_HISTORY_LIMIT,
    RECENT_CONTEXT_LIMIT,
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


# ---------------------------------------------------------------------------
# _extract_apartment_hint
# ---------------------------------------------------------------------------


class TestExtractApartmentHint:
    def test_extracts_full_word_apartamento(self):
        assert _extract_apartment_hint("Barulho no apartamento 302") == "302"

    def test_extracts_abbreviation_apto(self):
        assert _extract_apartment_hint("Relato sobre apto 12") == "12"

    def test_extracts_abbreviation_apt_dot(self):
        assert _extract_apartment_hint("Acesso no apt. 7") == "7"

    def test_extracts_abbreviation_ap(self):
        assert _extract_apartment_hint("Problema no ap 501") == "501"

    def test_returns_none_when_no_apartment_mentioned(self):
        assert _extract_apartment_hint("Barulho no corredor") is None

    def test_case_insensitive(self):
        assert _extract_apartment_hint("APARTAMENTO 203 com problema") == "203"

    def test_extracts_alphanumeric_apartment(self):
        result = _extract_apartment_hint("apartamento 12A")
        assert result == "12A"


# ---------------------------------------------------------------------------
# _cap_conversation_history
# ---------------------------------------------------------------------------


class TestCapConversationHistory:
    def test_returns_same_list_when_within_limit(self):
        """Lista menor que o limite deve ser retornada intacta."""
        history = [f"entry-{i}" for i in range(CONVERSATION_HISTORY_LIMIT - 1)]
        result = _cap_conversation_history(history)
        assert result == history

    def test_returns_same_list_exactly_at_limit(self):
        """Lista com tamanho exato do limite deve ser retornada intacta."""
        history = [f"entry-{i}" for i in range(CONVERSATION_HISTORY_LIMIT)]
        result = _cap_conversation_history(history)
        assert result == history

    def test_truncates_to_limit_when_over(self):
        """Lista maior que o limite deve ser truncada para CONVERSATION_HISTORY_LIMIT."""
        history = [f"entry-{i}" for i in range(CONVERSATION_HISTORY_LIMIT + 4)]
        result = _cap_conversation_history(history)
        assert len(result) == CONVERSATION_HISTORY_LIMIT

    def test_keeps_most_recent_entries_when_truncated(self):
        """Após truncamento, as entradas MAIS RECENTES (ao final) devem ser mantidas."""
        history = [f"entry-{i}" for i in range(CONVERSATION_HISTORY_LIMIT + 3)]
        result = _cap_conversation_history(history)
        # O último elemento da lista original deve estar presente
        assert history[-1] in result
        # O primeiro (mais antigo) deve ter sido descartado
        assert history[0] not in result

    def test_empty_history_returns_empty(self):
        assert _cap_conversation_history([]) == []


# ---------------------------------------------------------------------------
# _build_session_context
# ---------------------------------------------------------------------------


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

    def test_aggregate_context_when_no_apartment_hint(self):
        """Sem menção de apartamento, o contexto deve ser agregado (instrui uso de tool)."""
        records = [{"occurrence_id": "1", "apartment": "302"}]
        with patch(
            "condominium_incident_agent.nodes.prepare_context.load_session",
            return_value=records,
        ):
            context = _build_session_context(user_input="Barulho no corredor")
        assert "get_session_history" in context

    def test_granular_context_injected_when_apartment_found_in_input(self):
        """Com apartamento mencionado no relato e histórico correspondente,
        o contexto deve incluir detalhes das ocorrências anteriores."""
        records = [
            {
                "occurrence_id": "uuid-x",
                "reported_at": "2026-07-10T10:00:00Z",
                "category": "NOISE",
                "severity": "LOW",
                "summary": "Barulho anterior.",
                "apartment": "302",
                "building": "A",
            }
        ]
        with patch(
            "condominium_incident_agent.nodes.prepare_context.load_session",
            return_value=records,
        ):
            context = _build_session_context(user_input="Barulho no apartamento 302")
        assert "302" in context
        assert "NOISE" in context
        assert "Barulho anterior." in context

    def test_granular_context_falls_back_to_aggregate_when_no_match(self):
        """Apartamento mencionado mas sem histórico → contexto agregado."""
        records = [{"occurrence_id": "1", "apartment": "401"}]
        with patch(
            "condominium_incident_agent.nodes.prepare_context.load_session",
            return_value=records,
        ):
            context = _build_session_context(user_input="Barulho no apartamento 302")
        # Sem match de apartamento, deve cair no contexto agregado
        assert "get_session_history" in context

    def test_granular_context_capped_at_recent_context_limit(self):
        """Contexto granular deve incluir no máximo RECENT_CONTEXT_LIMIT ocorrências."""
        records = [
            {
                "occurrence_id": f"uuid-{i}",
                "reported_at": f"2026-07-{i:02d}T10:00:00Z",
                "category": "NOISE",
                "severity": "LOW",
                "summary": f"Ocorrência {i}",
                "apartment": "302",
                "building": "A",
            }
            for i in range(1, RECENT_CONTEXT_LIMIT + 5)
        ]
        with patch(
            "condominium_incident_agent.nodes.prepare_context.load_session",
            return_value=records,
        ):
            context = _build_session_context(user_input="Barulho no apartamento 302")
        # Conta quantas ocorrências foram injetadas verificando o padrão "uuid-"
        injected_count = context.count("uuid-")
        assert injected_count <= RECENT_CONTEXT_LIMIT

    def test_granular_context_includes_tool_precedence_note(self):
        """Contexto granular deve informar que a tool tem precedência."""
        records = [
            {
                "occurrence_id": "uuid-1",
                "reported_at": "2026-07-10T10:00:00Z",
                "category": "ACCESS",
                "severity": "LOW",
                "summary": "Acesso anterior.",
                "apartment": "101",
                "building": "A",
            }
        ]
        with patch(
            "condominium_incident_agent.nodes.prepare_context.load_session",
            return_value=records,
        ):
            context = _build_session_context(user_input="Ocorrência no apartamento 101")
        assert "get_session_history" in context
        assert "precedência" in context


# ---------------------------------------------------------------------------
# prepare_context (integração do nó)
# ---------------------------------------------------------------------------


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

    def test_conversation_history_capped_when_over_limit(self):
        """prepare_context deve truncar conversation_history ao limite antes de appendar."""
        # Cria um histórico com LIMIT + 2 entradas — após o cap deve sobrar LIMIT - 1,
        # mais a nova entrada = LIMIT no total.
        over_limit = [f"old-entry-{i}" for i in range(CONVERSATION_HISTORY_LIMIT + 2)]
        state = _make_state(conversation_history=over_limit)

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

        # O histórico resultante não pode ultrapassar LIMIT + 1
        # (o cap reduz para LIMIT, depois appendamos 1 novo prompt)
        assert len(result["conversation_history"]) <= CONVERSATION_HISTORY_LIMIT + 1

    def test_conversation_history_not_truncated_when_within_limit(self):
        """Histórico dentro do limite não deve ser truncado."""
        within_limit = [f"entry-{i}" for i in range(CONVERSATION_HISTORY_LIMIT - 1)]
        state = _make_state(conversation_history=within_limit)

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

        # Todas as entradas anteriores + 1 novo prompt
        assert len(result["conversation_history"]) == CONVERSATION_HISTORY_LIMIT

    def test_apartment_mentioned_in_relato_generates_granular_context(self):
        """Se o relato menciona apartamento com histórico, o prompt deve incluir detalhes."""
        records = [
            {
                "occurrence_id": "uuid-hist",
                "reported_at": "2026-07-01T10:00:00Z",
                "category": "NOISE",
                "severity": "LOW",
                "summary": "Barulho de música alta.",
                "apartment": "302",
                "building": "A",
            }
        ]
        state = _make_state(
            user_input="Barulho excessivo no apartamento 302",
            session_history=records,
        )
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
        # O contexto granular com ocorrências do apartamento 302 deve estar no prompt
        assert "302" in prompt
        assert "NOISE" in prompt
