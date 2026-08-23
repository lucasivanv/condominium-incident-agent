"""Testes unitários para o nó classify_incident."""

import json
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from condominium_incident_agent.enums import Category, Severity
from condominium_incident_agent.nodes.classify_incident import (
    _extract_json,
    _route_after_classify,
    classify_incident,
)


def _make_state(**kwargs) -> dict:
    base = {
        "user_input": "Barulho excessivo no apartamento 302, bloco A",
        "reported_by": "Porteiro Silva",
        "reported_at": "2026-07-14T22:00:00Z",
        "occurrence_id": "test-uuid-001",
        "conversation_history": [
            "Prompt completo de classificação para o LLM..."
        ],
        "session_history": [],
        "category": None,
        "severity": None,
        "involved_people": [],
        "apartment": None,
        "building": None,
        "summary": None,
        "resident_info": None,
        "classification_error": None,
    }
    base.update(kwargs)
    return base


def _valid_llm_response(
    category: str = "NOISE",
    severity: str = "LOW",
    apartment: str = "302",
    building: str = "A",
) -> str:
    payload = {
        "reasoning": {
            "base_severity": severity,
            "recurrence_detected": False,
            "recurrence_count": 0,
            "final_severity": severity,
        },
        "category": category,
        "severity": severity,
        "involved_people": ["João"],
        "apartment": apartment,
        "building": building,
        "summary": "Relato de barulho excessivo no apartamento 302.",
    }
    return json.dumps(payload)


def _mock_llm_chain(response_text: str, tool_calls: list | None = None) -> MagicMock:
    """Cria o mock da cadeia llm.bind_tools().with_retry()."""
    ai_msg = AIMessage(content=response_text, tool_calls=tool_calls or [])
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = ai_msg

    mock_bound = MagicMock()
    mock_bound.with_retry.return_value = mock_chain

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_bound

    return mock_llm


class TestClassifyIncident:
    def test_valid_response_populates_category_and_severity(self):
        """Resposta válida do LLM deve preencher category e severity."""
        state = _make_state()
        mock_llm = _mock_llm_chain(_valid_llm_response("NOISE", "LOW"))

        with patch(
            "condominium_incident_agent.nodes.classify_incident.get_llm",
            return_value=mock_llm,
        ):
            result = classify_incident(state)

        assert result["category"] == Category.NOISE
        assert result["severity"] == Severity.LOW
        assert result["classification_error"] is None

    def test_valid_response_populates_all_fields(self):
        """Todos os campos do JSON devem ser extraídos corretamente."""
        state = _make_state()
        mock_llm = _mock_llm_chain(_valid_llm_response("NOISE", "MEDIUM", "302", "A"))

        with patch(
            "condominium_incident_agent.nodes.classify_incident.get_llm",
            return_value=mock_llm,
        ):
            result = classify_incident(state)

        assert result["apartment"] == "302"
        assert result["building"] == "A"
        assert result["summary"] is not None
        assert "João" in result["involved_people"]

    def test_response_without_json_sets_classification_error(self):
        """Resposta sem JSON válido deve definir classification_error."""
        state = _make_state()
        mock_llm = _mock_llm_chain("Desculpe, não consegui classificar.")

        with patch(
            "condominium_incident_agent.nodes.classify_incident.get_llm",
            return_value=mock_llm,
        ):
            result = classify_incident(state)

        assert result["classification_error"] is not None
        assert result["category"] is None
        assert result["severity"] is None

    def test_json_missing_category_sets_classification_error(self):
        """JSON sem campo 'category' deve gerar classification_error."""
        payload = json.dumps({"severity": "LOW", "summary": "sem categoria"})
        state = _make_state()
        mock_llm = _mock_llm_chain(payload)

        with patch(
            "condominium_incident_agent.nodes.classify_incident.get_llm",
            return_value=mock_llm,
        ):
            result = classify_incident(state)

        assert result["classification_error"] is not None
        assert "category" in result["classification_error"].lower()

    def test_json_missing_severity_sets_classification_error(self):
        """JSON sem campo 'severity' deve gerar classification_error."""
        payload = json.dumps({"category": "NOISE", "summary": "sem severidade"})
        state = _make_state()
        mock_llm = _mock_llm_chain(payload)

        with patch(
            "condominium_incident_agent.nodes.classify_incident.get_llm",
            return_value=mock_llm,
        ):
            result = classify_incident(state)

        assert result["classification_error"] is not None
        assert "severity" in result["classification_error"].lower()

    def test_invalid_category_value_sets_classification_error(self):
        """Categoria inválida no JSON deve gerar classification_error."""
        payload = json.dumps({"category": "UNKNOWN_CATEGORY", "severity": "LOW"})
        state = _make_state()
        mock_llm = _mock_llm_chain(payload)

        with patch(
            "condominium_incident_agent.nodes.classify_incident.get_llm",
            return_value=mock_llm,
        ):
            result = classify_incident(state)

        assert result["classification_error"] is not None

    def test_invalid_severity_value_sets_classification_error(self):
        """Severidade inválida no JSON deve gerar classification_error."""
        payload = json.dumps({"category": "NOISE", "severity": "EXTREME"})
        state = _make_state()
        mock_llm = _mock_llm_chain(payload)

        with patch(
            "condominium_incident_agent.nodes.classify_incident.get_llm",
            return_value=mock_llm,
        ):
            result = classify_incident(state)

        assert result["classification_error"] is not None

    def test_conversation_history_updated_with_llm_response(self):
        """O histórico de conversação deve ser atualizado com a resposta do LLM."""
        state = _make_state()
        mock_llm = _mock_llm_chain(_valid_llm_response())

        with patch(
            "condominium_incident_agent.nodes.classify_incident.get_llm",
            return_value=mock_llm,
        ):
            result = classify_incident(state)

        # Histórico original tinha 1 item; deve ter pelo menos 2 após a classificação
        assert len(result["conversation_history"]) >= 2

    def test_high_severity_classified_correctly(self):
        """Severidade HIGH deve ser classificada como Severity.HIGH."""
        state = _make_state()
        mock_llm = _mock_llm_chain(_valid_llm_response("SECURITY", "HIGH"))

        with patch(
            "condominium_incident_agent.nodes.classify_incident.get_llm",
            return_value=mock_llm,
        ):
            result = classify_incident(state)

        assert result["severity"] == Severity.HIGH
        assert result["category"] == Category.SECURITY

    def test_all_categories_accepted(self):
        """Todas as categorias válidas do enum devem ser aceitas."""
        from condominium_incident_agent.enums import Category

        for cat in Category:
            state = _make_state()
            mock_llm = _mock_llm_chain(_valid_llm_response(cat.value, "LOW"))
            with patch(
                "condominium_incident_agent.nodes.classify_incident.get_llm",
                return_value=mock_llm,
            ):
                result = classify_incident(state)
            assert result["category"] == cat, f"Falhou para categoria: {cat}"


class TestRouteAfterClassify:
    def test_routes_to_save_occurrence_when_no_error(self):
        state = {"classification_error": None}
        assert _route_after_classify(state) == "save_occurrence"

    def test_routes_to_handle_error_when_error_present(self):
        state = {"classification_error": "Campo 'category' ausente."}
        assert _route_after_classify(state) == "handle_error"

    def test_routes_to_handle_error_when_error_is_empty_string(self):
        # String vazia é falsy — deve rotear para save_occurrence
        state = {"classification_error": ""}
        assert _route_after_classify(state) == "save_occurrence"


class TestExtractJson:
    def test_extracts_json_from_plain_text(self):
        text = 'Aqui está o resultado: {"category": "NOISE", "severity": "LOW"}'
        result = _extract_json(text)
        assert result["category"] == "NOISE"

    def test_extracts_json_from_markdown_code_block(self):
        text = '```json\n{"category": "MAINTENANCE", "severity": "MEDIUM"}\n```'
        result = _extract_json(text)
        assert result["severity"] == "MEDIUM"

    def test_raises_value_error_when_no_json(self):
        with pytest.raises(ValueError, match="Nenhum JSON válido"):
            _extract_json("Texto sem JSON nenhum aqui.")

    def test_extracts_first_json_when_multiple(self):
        text = '{"category": "NOISE"} e também {"category": "OTHER"}'
        result = _extract_json(text)
        assert result["category"] == "NOISE"

    def test_handles_nested_json(self):
        payload = {
            "category": "NOISE",
            "severity": "LOW",
            "reasoning": {"base": "LOW", "final": "LOW"},
        }
        text = json.dumps(payload)
        result = _extract_json(text)
        assert result["reasoning"]["base"] == "LOW"
