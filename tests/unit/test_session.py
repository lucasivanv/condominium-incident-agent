"""Testes unitários para o módulo session (load_session / append_to_session)."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import condominium_incident_agent.session as session_module
from condominium_incident_agent.session import load_session, append_to_session


@pytest.fixture()
def patch_session_file(tmp_path, monkeypatch):
    """Redireciona SESSION_FILE para um arquivo temporário."""
    temp_file = tmp_path / "session.json"
    monkeypatch.setattr(session_module, "SESSION_FILE", temp_file)
    return temp_file


class TestLoadSession:
    def test_returns_empty_list_when_file_does_not_exist(self, patch_session_file):
        """Arquivo inexistente deve retornar lista vazia sem exceção."""
        result = load_session()
        assert result == []

    def test_returns_records_from_valid_file(self, patch_session_file):
        """Arquivo válido deve retornar os registros corretamente."""
        records = [
            {"occurrence_id": "uuid-1", "category": "NOISE"},
            {"occurrence_id": "uuid-2", "category": "ACCESS"},
        ]
        patch_session_file.write_text(
            json.dumps(records, ensure_ascii=False), encoding="utf-8"
        )
        result = load_session()
        assert len(result) == 2
        assert result[0]["occurrence_id"] == "uuid-1"

    def test_returns_empty_list_on_corrupted_json(self, patch_session_file):
        """JSON corrompido deve retornar lista vazia sem lançar exceção."""
        patch_session_file.write_text("{ invalid json }", encoding="utf-8")
        result = load_session()
        assert result == []

    def test_returns_empty_list_on_empty_file(self, patch_session_file):
        """Arquivo vazio deve retornar lista vazia sem exceção."""
        patch_session_file.write_text("", encoding="utf-8")
        result = load_session()
        assert result == []

    def test_preserves_all_fields(self, patch_session_file):
        """Todos os campos dos registros devem ser preservados na leitura."""
        record = {
            "occurrence_id": "uuid-1",
            "category": "NOISE",
            "severity": "LOW",
            "apartment": "302",
            "building": "A",
            "summary": "Barulho",
        }
        patch_session_file.write_text(
            json.dumps([record], ensure_ascii=False), encoding="utf-8"
        )
        result = load_session()
        assert result[0] == record


class TestAppendToSession:
    def test_creates_file_when_not_exists(self, patch_session_file):
        """append_to_session deve criar o arquivo quando não existir."""
        entry = {"occurrence_id": "new-uuid", "category": "NOISE"}
        append_to_session(entry)

        assert patch_session_file.exists()
        records = json.loads(patch_session_file.read_text(encoding="utf-8"))
        assert len(records) == 1
        assert records[0]["occurrence_id"] == "new-uuid"

    def test_appends_to_existing_records(self, patch_session_file):
        """Nova entrada deve ser adicionada sem remover as existentes."""
        existing = [{"occurrence_id": "old-uuid", "category": "ACCESS"}]
        patch_session_file.write_text(
            json.dumps(existing, ensure_ascii=False), encoding="utf-8"
        )

        new_entry = {"occurrence_id": "new-uuid", "category": "NOISE"}
        append_to_session(new_entry)

        records = json.loads(patch_session_file.read_text(encoding="utf-8"))
        assert len(records) == 2
        assert records[0]["occurrence_id"] == "old-uuid"
        assert records[1]["occurrence_id"] == "new-uuid"

    def test_creates_parent_directory_if_not_exists(self, tmp_path, monkeypatch):
        """Deve criar diretórios intermediários se não existirem."""
        nested_file = tmp_path / "nested" / "deep" / "session.json"
        monkeypatch.setattr(session_module, "SESSION_FILE", nested_file)

        append_to_session({"occurrence_id": "uuid-x"})

        assert nested_file.exists()

    def test_handles_corrupted_existing_file(self, patch_session_file):
        """Arquivo corrompido deve ser reiniciado com a nova entrada."""
        patch_session_file.write_text("não é json válido", encoding="utf-8")
        entry = {"occurrence_id": "recovery-uuid"}
        append_to_session(entry)

        records = json.loads(patch_session_file.read_text(encoding="utf-8"))
        assert len(records) == 1
        assert records[0]["occurrence_id"] == "recovery-uuid"

    def test_multiple_appends_accumulate(self, patch_session_file):
        """Múltiplos appends sucessivos devem acumular corretamente."""
        for i in range(5):
            append_to_session({"occurrence_id": f"uuid-{i}"})

        records = json.loads(patch_session_file.read_text(encoding="utf-8"))
        assert len(records) == 5
        assert records[4]["occurrence_id"] == "uuid-4"
