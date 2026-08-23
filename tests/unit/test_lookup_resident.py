"""Testes unitários para a tool lookup_resident."""

from unittest.mock import patch

from condominium_incident_agent.tools.lookup_resident import lookup_resident


_RESIDENTS_FIXTURE = [
    {
        "apartment": "302",
        "building": "A",
        "resident_name": "Maria Oliveira",
        "authorized_visitors": ["Carlos", "Ana"],
        "vehicles": ["ABC-1234"],
        "phone": "(**) ****-9001",
    },
    {
        "apartment": "401",
        "building": "B",
        "resident_name": "João Santos",
        "authorized_visitors": [],
        "vehicles": [],
        "phone": "(**) ****-9002",
    },
    {
        "apartment": "101",
        "building": "A",
        "resident_name": "Pedro Costa",
        "authorized_visitors": ["Mariana"],
        "vehicles": ["XYZ-5678"],
        "phone": "(**) ****-9003",
    },
]


def _invoke(apartment: str, building: str | None = None) -> dict:
    """Invoca a tool lookup_resident desempacotando o retorno."""
    # LangChain @tool wraps the function; podemos chamar .invoke() ou direto
    return lookup_resident.invoke({"apartment": apartment, "building": building})


class TestLookupResident:
    def test_found_returns_resident_data(self):
        """Apartamento cadastrado deve retornar found=True e dados do morador."""
        with patch(
            "condominium_incident_agent.tools.lookup_resident._load_residents",
            return_value=_RESIDENTS_FIXTURE,
        ):
            result = _invoke("302", "A")

        assert result["found"] is True
        assert result["resident_name"] == "Maria Oliveira"
        assert result["apartment"] == "302"
        assert result["building"] == "A"

    def test_not_found_returns_found_false(self):
        """Apartamento inexistente deve retornar found=False."""
        with patch(
            "condominium_incident_agent.tools.lookup_resident._load_residents",
            return_value=_RESIDENTS_FIXTURE,
        ):
            result = _invoke("999", "Z")

        assert result["found"] is False

    def test_search_is_case_insensitive(self):
        """Busca deve ser insensível a maiúsculas/minúsculas."""
        with patch(
            "condominium_incident_agent.tools.lookup_resident._load_residents",
            return_value=_RESIDENTS_FIXTURE,
        ):
            result = _invoke("302", "a")  # 'a' minúsculo deve bater com 'A'

        assert result["found"] is True
        assert result["resident_name"] == "Maria Oliveira"

    def test_search_without_building_matches_any(self):
        """Busca sem building deve retornar o primeiro apartamento correspondente."""
        with patch(
            "condominium_incident_agent.tools.lookup_resident._load_residents",
            return_value=_RESIDENTS_FIXTURE,
        ):
            result = _invoke("401")  # sem building

        assert result["found"] is True
        assert result["resident_name"] == "João Santos"

    def test_building_filter_excludes_wrong_block(self):
        """Busca com building errado deve retornar found=False."""
        with patch(
            "condominium_incident_agent.tools.lookup_resident._load_residents",
            return_value=_RESIDENTS_FIXTURE,
        ):
            result = _invoke("302", "B")  # apt 302 está no bloco A, não B

        assert result["found"] is False

    def test_authorized_visitors_returned(self):
        """Visitantes autorizados devem ser incluídos no retorno."""
        with patch(
            "condominium_incident_agent.tools.lookup_resident._load_residents",
            return_value=_RESIDENTS_FIXTURE,
        ):
            result = _invoke("302", "A")

        assert "Carlos" in result["authorized_visitors"]
        assert "Ana" in result["authorized_visitors"]

    def test_vehicles_returned(self):
        """Veículos cadastrados devem ser incluídos no retorno."""
        with patch(
            "condominium_incident_agent.tools.lookup_resident._load_residents",
            return_value=_RESIDENTS_FIXTURE,
        ):
            result = _invoke("302", "A")

        assert "ABC-1234" in result["vehicles"]

    def test_empty_residents_list_returns_not_found(self):
        """Lista vazia de moradores deve retornar found=False."""
        with patch(
            "condominium_incident_agent.tools.lookup_resident._load_residents",
            return_value=[],
        ):
            result = _invoke("302", "A")

        assert result["found"] is False

    def test_not_found_response_includes_queried_apartment(self):
        """Resposta not-found deve incluir o apartamento consultado."""
        with patch(
            "condominium_incident_agent.tools.lookup_resident._load_residents",
            return_value=[],
        ):
            result = _invoke("999")

        assert result["apartment"] == "999"

    def test_input_with_whitespace_trimmed(self):
        """Espaços em torno do apartamento devem ser ignorados na busca."""
        with patch(
            "condominium_incident_agent.tools.lookup_resident._load_residents",
            return_value=_RESIDENTS_FIXTURE,
        ):
            result = _invoke("  302  ", "  A  ")

        assert result["found"] is True
