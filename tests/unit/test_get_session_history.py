"""Testes unitários para a tool get_session_history."""

from unittest.mock import patch

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
