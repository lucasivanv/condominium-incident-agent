"""Testes unitários para o nó save_occurrence."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

from condominium_incident_agent.enums import Category, Severity
from condominium_incident_agent.nodes.save_occurrence import save_occurrence
from condominium_incident_agent.security import create_human_approval


def _make_state(**kwargs) -> dict:
    """Estado base com ocorrência classificada e pronta para persistência."""
    base = {
        "occurrence_id": "test-uuid-001",
        "user_input": "Barulho excessivo no apartamento 302",
        "reported_by": "Porteiro Silva",
        "reported_at": "2026-07-14T22:00:00Z",
        "category": Category.NOISE,
        "severity": Severity.LOW,
        "involved_people": ["João"],
        "apartment": "302",
        "building": "A",
        "summary": "Relato de barulho excessivo.",
        "resident_info": None,
        "output_file": None,
        "escalated_file": None,
        "classification_error": None,
        "multiple_incidents_detected": False,
        "conversation_history": [],
        "session_history": [],
    }
    base.update(kwargs)
    return base


class TestSaveOccurrence:
    def test_persistence_failure_returns_controlled_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.REPORTS_DIR", tmp_path
        )
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.append_to_session",
            MagicMock(side_effect=OSError("session disk unavailable")),
        )

        result = save_occurrence(_make_state())

        assert result["classification_error"] is not None
        assert result["output_file"] is None
        assert result["escalated_file"] is None

    def test_output_file_is_written_atomically(self, tmp_path, monkeypatch):
        """O relatório principal deve ser substituído após a escrita completa."""
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.REPORTS_DIR", tmp_path
        )
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.ESCALATED_DIR",
            tmp_path / "escalated",
        )
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.append_to_session",
            MagicMock(),
        )
        replace_calls: list[tuple[str, str]] = []
        original_replace = os.replace

        def spy_replace(source: str, destination: str) -> None:
            replace_calls.append((source, destination))
            original_replace(source, destination)

        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.os.replace",
            spy_replace,
        )

        result = save_occurrence(_make_state())

        assert len(replace_calls) == 1
        assert Path(replace_calls[0][1]) == Path(result["output_file"])

    def test_output_file_created_with_correct_content(self, tmp_path, monkeypatch):
        """O arquivo JSON da ocorrência deve ser criado com os dados corretos."""
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.REPORTS_DIR", tmp_path
        )
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.ESCALATED_DIR",
            tmp_path / "escalated",
        )
        mock_append = MagicMock()
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.append_to_session",
            mock_append,
        )

        state = _make_state()
        result = save_occurrence(state)

        output_path = Path(result["output_file"])
        assert output_path.exists()

        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert data["occurrence_id"] == "test-uuid-001"
        assert data["category"] == "NOISE"
        assert data["severity"] == "LOW"
        assert data["apartment"] == "302"

    def test_secrets_are_redacted_from_report_and_session_entry(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.REPORTS_DIR", tmp_path
        )
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.ESCALATED_DIR",
            tmp_path / "escalated",
        )
        mock_append = MagicMock()
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.append_to_session",
            mock_append,
        )
        state = _make_state(
            user_input="Relato token=input-secret",
            reported_by="Porteiro token=reporter-secret",
            apartment="token=apartment-secret",
            summary="Resumo token=summary-secret",
        )

        result = save_occurrence(state)

        persisted = Path(result["output_file"]).read_text(encoding="utf-8")
        session_entry = json.dumps(mock_append.call_args.args[0], ensure_ascii=False)
        for secret in (
            "input-secret",
            "reporter-secret",
            "apartment-secret",
            "summary-secret",
        ):
            assert secret not in persisted
            assert secret not in session_entry
        assert "[REDACTED]" in persisted
        assert "[REDACTED]" in session_entry

    def test_output_file_path_set_in_state(self, tmp_path, monkeypatch):
        """O campo output_file no estado deve apontar para o arquivo criado."""
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.REPORTS_DIR", tmp_path
        )
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.ESCALATED_DIR",
            tmp_path / "escalated",
        )
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.append_to_session",
            MagicMock(),
        )

        result = save_occurrence(_make_state())

        assert result["output_file"] is not None
        assert Path(result["output_file"]).exists()

    def test_escalated_file_not_created_for_low_severity(self, tmp_path, monkeypatch):
        """Ocorrências LOW não devem gerar arquivo em escalated/."""
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.REPORTS_DIR", tmp_path
        )
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.ESCALATED_DIR",
            tmp_path / "escalated",
        )
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.append_to_session",
            MagicMock(),
        )

        result = save_occurrence(_make_state(severity=Severity.LOW))

        assert result["escalated_file"] is None
        escalated_dir = tmp_path / "escalated"
        # Pasta pode não existir ou estar vazia
        assert not escalated_dir.exists() or len(list(escalated_dir.iterdir())) == 0

    def test_escalated_file_created_for_high_severity(self, tmp_path, monkeypatch):
        """Ocorrências HIGH devem gerar arquivo adicional em escalated/."""
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.REPORTS_DIR", tmp_path
        )
        escalated_dir = tmp_path / "escalated"
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.ESCALATED_DIR",
            escalated_dir,
        )
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.append_to_session",
            MagicMock(),
        )

        monkeypatch.setenv("HUMAN_APPROVAL_SECRET", "unit-test-secret")
        state = _make_state(
            severity=Severity.HIGH,
            category=Category.SECURITY,
            human_approval=create_human_approval(
                "test-uuid-001", "admin", "2099-01-01T00:00:00+00:00"
            ),
        )
        result = save_occurrence(state)

        assert result["escalated_file"] is not None
        escalated_path = Path(result["escalated_file"])
        assert escalated_path.exists()

        data = json.loads(escalated_path.read_text(encoding="utf-8"))
        assert data["escalated"] is True
        assert "escalated_at" in data

    def test_escalated_file_not_created_for_medium_severity(self, tmp_path, monkeypatch):
        """Ocorrências MEDIUM não devem gerar arquivo escalated."""
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.REPORTS_DIR", tmp_path
        )
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.ESCALATED_DIR",
            tmp_path / "escalated",
        )
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.append_to_session",
            MagicMock(),
        )

        result = save_occurrence(_make_state(severity=Severity.MEDIUM))
        assert result["escalated_file"] is None

    def test_append_to_session_called_once(self, tmp_path, monkeypatch):
        """append_to_session deve ser chamado exatamente uma vez."""
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.REPORTS_DIR", tmp_path
        )
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.ESCALATED_DIR",
            tmp_path / "escalated",
        )
        mock_append = MagicMock()
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.append_to_session",
            mock_append,
        )

        save_occurrence(_make_state())

        mock_append.assert_called_once()

    def test_append_to_session_called_with_correct_fields(self, tmp_path, monkeypatch):
        """append_to_session deve receber os campos esperados."""
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.REPORTS_DIR", tmp_path
        )
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.ESCALATED_DIR",
            tmp_path / "escalated",
        )
        mock_append = MagicMock()
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.append_to_session",
            mock_append,
        )

        save_occurrence(_make_state())

        call_args = mock_append.call_args[0][0]
        assert call_args["occurrence_id"] == "test-uuid-001"
        assert call_args["category"] == "NOISE"
        assert call_args["severity"] == "LOW"

    def test_session_history_updated_in_memory(self, tmp_path, monkeypatch):
        """session_history no estado deve ser atualizado com a nova ocorrência."""
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.REPORTS_DIR", tmp_path
        )
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.ESCALATED_DIR",
            tmp_path / "escalated",
        )
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.append_to_session",
            MagicMock(),
        )

        state = _make_state(session_history=[])
        result = save_occurrence(state)

        assert len(result["session_history"]) == 1
        assert result["session_history"][0]["occurrence_id"] == "test-uuid-001"

    def test_session_history_appended_to_existing(self, tmp_path, monkeypatch):
        """session_history existente deve ser preservado e a nova entrada adicionada."""
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.REPORTS_DIR", tmp_path
        )
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.ESCALATED_DIR",
            tmp_path / "escalated",
        )
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.append_to_session",
            MagicMock(),
        )

        existing_entry = {"occurrence_id": "old-uuid", "category": "NOISE"}
        state = _make_state(session_history=[existing_entry])
        result = save_occurrence(state)

        assert len(result["session_history"]) == 2
        assert result["session_history"][0]["occurrence_id"] == "old-uuid"
        assert result["session_history"][1]["occurrence_id"] == "test-uuid-001"

    def test_filename_contains_occurrence_id(self, tmp_path, monkeypatch):
        """O nome do arquivo JSON deve conter o occurrence_id."""
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.REPORTS_DIR", tmp_path
        )
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.ESCALATED_DIR",
            tmp_path / "escalated",
        )
        monkeypatch.setattr(
            "condominium_incident_agent.nodes.save_occurrence.append_to_session",
            MagicMock(),
        )

        result = save_occurrence(_make_state(occurrence_id="my-special-uuid"))

        assert "my-special-uuid" in result["output_file"]
