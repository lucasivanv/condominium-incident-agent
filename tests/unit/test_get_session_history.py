"""Testes unitários para a tool get_session_history."""

from unittest.mock import patch

from condominium_incident_agent.session import RECENT_CONTEXT_LIMIT
from condominium_incident_agent.tools.get_session_history import get_session_history

_SESSION_FIXTURE = [
    {
        "occurrence_id": "uuid-1",
        "reported_at": "2026-07-14T20:00:00Z",
        "reported_by": "Porteiro Silva",
        "category": "NOISE",
        "severity": "LOW",
        "summary": "Barulho no corredor.",
        "apartment": "302",
        "building": "A",
    },
    {
        "occurrence_id": "uuid-2",
        "reported_at": "2026-07-15T10:00:00Z",
        "reported_by": "Porteiro João",
        "category": "NOISE",
        "severity": "MEDIUM",
        "summary": "Barulho repetido.",
        "apartment": "302",
        "building": "A",
    },
    {
        "occurrence_id": "uuid-3",
        "reported_at": "2026-07-16T08:00:00Z",
        "reported_by": "Porteiro Silva",
        "category": "ACCESS",
        "severity": "HIGH",
        "summary": "Acesso não autorizado.",
        "apartment": "401",
        "building": "B",
    },
]


def _invoke(apartment: str, building: str | None = None) -> dict:
    return get_session_history.invoke({"apartment": apartment, "building": building})


class TestGetSessionHistory:
    def test_no_history_returns_found_false(self):
        """Sessão vazia deve retornar found=False e total=0."""
        with patch(
            "condominium_incident_agent.tools.get_session_history.load_session",
            return_value=[],
        ):
            result = _invoke("302", "A")

        assert result["found"] is False
        assert result["total"] == 0
        assert result["occurrences"] == []

    def test_existing_history_returns_found_true(self):
        """Histórico existente para o apartamento deve retornar found=True."""
        with patch(
            "condominium_incident_agent.tools.get_session_history.load_session",
            return_value=_SESSION_FIXTURE,
        ):
            result = _invoke("302", "A")

        assert result["found"] is True
        assert result["total"] == 2

    def test_occurrences_list_contains_correct_fields(self):
        """Cada ocorrência retornada deve conter os campos esperados."""
        with patch(
            "condominium_incident_agent.tools.get_session_history.load_session",
            return_value=_SESSION_FIXTURE,
        ):
            result = _invoke("302", "A")

        for occurrence in result["occurrences"]:
            assert "occurrence_id" in occurrence
            assert "reported_at" in occurrence
            assert "category" in occurrence
            assert "severity" in occurrence
            assert "summary" in occurrence

    def test_filters_by_apartment_and_building(self):
        """Apenas ocorrências do apartamento e bloco corretos devem ser retornadas."""
        with patch(
            "condominium_incident_agent.tools.get_session_history.load_session",
            return_value=_SESSION_FIXTURE,
        ):
            result = _invoke("401", "B")

        assert result["total"] == 1
        assert result["occurrences"][0]["occurrence_id"] == "uuid-3"

    def test_search_without_building_returns_all_for_apartment(self):
        """Sem building, retorna ocorrências do apartamento independente do bloco."""
        fixture = [
            {
                "occurrence_id": "uuid-A",
                "reported_at": "2026-07-14T20:00:00Z",
                "category": "NOISE",
                "severity": "LOW",
                "summary": "s",
                "apartment": "302",
                "building": "A",
            },
            {
                "occurrence_id": "uuid-B",
                "reported_at": "2026-07-15T10:00:00Z",
                "category": "NOISE",
                "severity": "LOW",
                "summary": "s",
                "apartment": "302",
                "building": "B",
            },
        ]
        with patch(
            "condominium_incident_agent.tools.get_session_history.load_session",
            return_value=fixture,
        ):
            result = _invoke("302")  # sem building

        assert result["total"] == 2

    def test_search_is_case_insensitive(self):
        """Busca deve ser insensível a maiúsculas/minúsculas."""
        with patch(
            "condominium_incident_agent.tools.get_session_history.load_session",
            return_value=_SESSION_FIXTURE,
        ):
            result = _invoke("302", "a")  # 'a' minúsculo deve bater com 'A'

        assert result["found"] is True

    def test_not_found_for_unknown_apartment(self):
        """Apartamento sem histórico deve retornar found=False."""
        with patch(
            "condominium_incident_agent.tools.get_session_history.load_session",
            return_value=_SESSION_FIXTURE,
        ):
            result = _invoke("999", "Z")

        assert result["found"] is False
        assert result["total"] == 0

    def test_response_includes_apartment_queried(self):
        """A resposta deve incluir o apartamento consultado."""
        with patch(
            "condominium_incident_agent.tools.get_session_history.load_session",
            return_value=[],
        ):
            result = _invoke("502")

        assert result["apartment"] == "502"

    def test_message_field_present_in_response(self):
        """Campo 'message' deve estar presente na resposta."""
        with patch(
            "condominium_incident_agent.tools.get_session_history.load_session",
            return_value=_SESSION_FIXTURE,
        ):
            result = _invoke("302", "A")

        assert "message" in result
        assert len(result["message"]) > 0

    def test_returned_field_present_in_found_response(self):
        """Campo 'returned' deve estar presente quando ocorrências são encontradas."""
        with patch(
            "condominium_incident_agent.tools.get_session_history.load_session",
            return_value=_SESSION_FIXTURE,
        ):
            result = _invoke("302", "A")

        assert "returned" in result
        assert result["returned"] == result["total"]

    def test_returned_field_present_in_not_found_response(self):
        """Campo 'returned' deve estar presente mesmo quando nada é encontrado."""
        with patch(
            "condominium_incident_agent.tools.get_session_history.load_session",
            return_value=[],
        ):
            result = _invoke("999")

        assert "returned" in result
        assert result["returned"] == 0


class TestGetSessionHistoryLimit:
    """Testa o comportamento de limitação de contexto (RECENT_CONTEXT_LIMIT)."""

    def _make_fixture(self, n: int, apartment: str = "101") -> list[dict]:
        """Gera N entradas para o apartamento informado em ordem cronológica."""
        return [
            {
                "occurrence_id": f"uuid-{i}",
                "reported_at": f"2026-07-{i + 1:02d}T10:00:00Z",
                "category": "NOISE",
                "severity": "LOW",
                "summary": f"Ocorrência {i}",
                "apartment": apartment,
                "building": "A",
            }
            for i in range(1, n + 1)
        ]

    def test_returns_at_most_recent_context_limit_occurrences(self):
        """Deve retornar no máximo RECENT_CONTEXT_LIMIT ocorrências."""
        many = self._make_fixture(RECENT_CONTEXT_LIMIT + 5)
        with patch(
            "condominium_incident_agent.tools.get_session_history.load_session",
            return_value=many,
        ):
            result = _invoke("101", "A")

        assert result["found"] is True
        assert len(result["occurrences"]) == RECENT_CONTEXT_LIMIT
        assert result["returned"] == RECENT_CONTEXT_LIMIT

    def test_total_reflects_all_records_not_just_returned(self):
        """Campo 'total' deve refletir o número real de registros, não o limite."""
        over_limit = RECENT_CONTEXT_LIMIT + 3
        many = self._make_fixture(over_limit)
        with patch(
            "condominium_incident_agent.tools.get_session_history.load_session",
            return_value=many,
        ):
            result = _invoke("101", "A")

        assert result["total"] == over_limit
        assert result["returned"] == RECENT_CONTEXT_LIMIT

    def test_most_recent_occurrences_are_returned_when_truncated(self):
        """Quando truncado, as ocorrências MAIS RECENTES (ao final da lista) devem ser retornadas."""
        many = self._make_fixture(RECENT_CONTEXT_LIMIT + 2)
        with patch(
            "condominium_incident_agent.tools.get_session_history.load_session",
            return_value=many,
        ):
            result = _invoke("101", "A")

        returned_ids = [occ["occurrence_id"] for occ in result["occurrences"]]
        # O último uuid gerado deve estar presente; o primeiro (uuid-1) deve ter sido descartado
        assert f"uuid-{RECENT_CONTEXT_LIMIT + 2}" in returned_ids
        assert "uuid-1" not in returned_ids

    def test_truncation_note_in_message_when_limited(self):
        """Mensagem deve mencionar exibição parcial quando o limite for atingido."""
        many = self._make_fixture(RECENT_CONTEXT_LIMIT + 1)
        with patch(
            "condominium_incident_agent.tools.get_session_history.load_session",
            return_value=many,
        ):
            result = _invoke("101", "A")

        assert "exibindo" in result["message"].lower() or str(RECENT_CONTEXT_LIMIT) in result["message"]

    def test_no_truncation_note_when_within_limit(self):
        """Mensagem não deve mencionar truncamento quando total <= limite."""
        few = self._make_fixture(RECENT_CONTEXT_LIMIT - 1)
        with patch(
            "condominium_incident_agent.tools.get_session_history.load_session",
            return_value=few,
        ):
            result = _invoke("101", "A")

        assert "exibindo" not in result["message"].lower()

    def test_returns_all_when_exactly_at_limit(self):
        """Quando total == RECENT_CONTEXT_LIMIT, todos devem ser retornados sem nota."""
        exactly = self._make_fixture(RECENT_CONTEXT_LIMIT)
        with patch(
            "condominium_incident_agent.tools.get_session_history.load_session",
            return_value=exactly,
        ):
            result = _invoke("101", "A")

        assert result["total"] == RECENT_CONTEXT_LIMIT
        assert result["returned"] == RECENT_CONTEXT_LIMIT
        assert "exibindo" not in result["message"].lower()

    def test_ignores_records_with_missing_apartment_or_building(self):
        """Campos opcionais nulos não devem interromper a consulta."""
        records = [
            {"occurrence_id": "without-apartment", "apartment": None, "building": None},
            {
                "occurrence_id": "matching",
                "apartment": "101",
                "building": "A",
                "category": "NOISE",
            },
        ]
        with patch(
            "condominium_incident_agent.tools.get_session_history.load_session",
            return_value=records,
        ):
            result = _invoke("101", "A")

        assert result["found"] is True
        assert [occ["occurrence_id"] for occ in result["occurrences"]] == ["matching"]
