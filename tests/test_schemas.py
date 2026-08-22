"""Unit tests for schemas, enums, and state — no LLM or Ollama required."""

import pytest
from pydantic import ValidationError

from incident_classification_agent.enums import Category, Severity
from incident_classification_agent.schemas import IncidentInput


class TestIncidentInput:
    def test_valid_input_minimal(self):
        data = {"user_input": "Barulho no corredor", "reported_by": "Porteiro João"}
        obj = IncidentInput(**data)
        assert obj.user_input == "Barulho no corredor"
        assert obj.reported_by == "Porteiro João"
        assert obj.reported_at is not None

    def test_valid_input_with_reported_at(self):
        data = {
            "user_input": "Pacote extraviado",
            "reported_by": "Maria",
            "reported_at": "2026-07-14T22:18:42Z",
        }
        obj = IncidentInput(**data)
        assert obj.reported_at.tzinfo is not None

    def test_blank_user_input_rejected(self):
        with pytest.raises(ValidationError):
            IncidentInput(user_input="   ", reported_by="João")

    def test_blank_reported_by_rejected(self):
        with pytest.raises(ValidationError):
            IncidentInput(user_input="Incidente", reported_by="")

    def test_missing_user_input_rejected(self):
        with pytest.raises(ValidationError):
            IncidentInput(reported_by="João")

    def test_missing_reported_by_rejected(self):
        with pytest.raises(ValidationError):
            IncidentInput(user_input="Incidente")

    def test_to_initial_state_keys(self):
        obj = IncidentInput(user_input="Teste", reported_by="Porteiro")
        state = obj.to_initial_state()
        expected_keys = {
            "user_input",
            "reported_by",
            "reported_at",
            "occurrence_id",
            "category",
            "severity",
            "involved_people",
            "apartment",
            "building",
            "summary",
            "conversation_history",
            "output_file",
            "escalated_file",
            "classification_error",
            "resident_info",
            "multiple_incidents_detected",
            "session_history",
        }
        assert expected_keys == set(state.keys())

    def test_to_initial_state_defaults(self):
        obj = IncidentInput(user_input="  Teste  ", reported_by="  Porteiro  ")
        state = obj.to_initial_state()
        assert state["user_input"] == "Teste"
        assert state["reported_by"] == "Porteiro"
        assert state["occurrence_id"] is None
        assert state["category"] is None
        assert state["severity"] is None
        assert state["involved_people"] == []
        assert state["conversation_history"] == []
        assert state["session_history"] == []

    def test_reported_at_utc_format(self):
        obj = IncidentInput(user_input="Teste", reported_by="Porteiro")
        state = obj.to_initial_state()
        # Must be in the format YYYY-MM-DDTHH:MM:SSZ
        assert state["reported_at"].endswith("Z")


class TestEnums:
    def test_category_values(self):
        assert Category.ACCESS.value == "ACCESS"
        assert Category.PACKAGE.value == "PACKAGE"
        assert Category.NOISE.value == "NOISE"
        assert Category.MAINTENANCE.value == "MAINTENANCE"
        assert Category.SECURITY.value == "SECURITY"
        assert Category.OTHER.value == "OTHER"

    def test_severity_values(self):
        assert Severity.LOW.value == "LOW"
        assert Severity.MEDIUM.value == "MEDIUM"
        assert Severity.HIGH.value == "HIGH"

    def test_category_from_string(self):
        assert Category("ACCESS") is Category.ACCESS
        assert Category("NOISE") is Category.NOISE

    def test_severity_from_string(self):
        assert Severity("LOW") is Severity.LOW
        assert Severity("HIGH") is Severity.HIGH

    def test_invalid_category_raises(self):
        with pytest.raises(ValueError):
            Category("UNKNOWN")

    def test_invalid_severity_raises(self):
        with pytest.raises(ValueError):
            Severity("CRITICAL")
