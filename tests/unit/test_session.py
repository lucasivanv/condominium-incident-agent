"""Testes unitários para o módulo session.py.

Cobre:
- load_session: arquivo ausente, corrompido, formato inesperado
- append_to_session: escrita atômica (arquivo temporário substituído),
  acumulação de múltiplas entradas sem perda de dados
- Constantes de limite: RECENT_CONTEXT_LIMIT e CONVERSATION_HISTORY_LIMIT
"""

import json
import os
from pathlib import Path

import pytest

import condominium_incident_agent.session as session_module
from condominium_incident_agent.session import (
    CONVERSATION_HISTORY_LIMIT,
    RECENT_CONTEXT_LIMIT,
    append_to_session,
    load_session,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_session(tmp_path, monkeypatch):
    """Redireciona SESSION_FILE para tmp_path em todos os testes deste módulo."""
    session_file = tmp_path / "session.json"
    monkeypatch.setattr(session_module, "SESSION_FILE", session_file)
    yield session_file


# ---------------------------------------------------------------------------
# load_session
# ---------------------------------------------------------------------------


class TestLoadSession:
    def test_returns_empty_list_when_file_absent(self, _isolated_session):
        """Deve retornar lista vazia quando o arquivo não existe."""
        assert not _isolated_session.exists()
        assert load_session() == []

    def test_returns_empty_list_on_corrupted_json(self, _isolated_session):
        """Deve retornar lista vazia e não lançar exceção em JSON corrompido."""
        _isolated_session.write_text("{broken json", encoding="utf-8")
        assert load_session() == []

    def test_returns_empty_list_when_content_is_not_a_list(self, _isolated_session):
        """JSON válido mas não-lista deve ser tratado como sessão vazia."""
        _isolated_session.write_text(json.dumps({"key": "value"}), encoding="utf-8")
        assert load_session() == []

    def test_returns_records_from_valid_file(self, _isolated_session):
        """Arquivo válido deve retornar todos os registros."""
        records = [{"occurrence_id": "a"}, {"occurrence_id": "b"}]
        _isolated_session.write_text(json.dumps(records), encoding="utf-8")
        assert load_session() == records

    def test_preserves_all_fields_in_records(self, _isolated_session):
        """Todos os campos de cada registro devem ser preservados na leitura."""
        entry = {
            "occurrence_id": "uuid-1",
            "apartment": "302",
            "building": "A",
            "category": "NOISE",
            "severity": "LOW",
            "summary": "barulho",
        }
        _isolated_session.write_text(json.dumps([entry]), encoding="utf-8")
        result = load_session()
        assert result[0] == entry


# ---------------------------------------------------------------------------
# append_to_session
# ---------------------------------------------------------------------------


class TestAppendToSession:
    def test_creates_file_on_first_append(self, _isolated_session):
        """Primeira chamada deve criar o session.json."""
        assert not _isolated_session.exists()
        append_to_session({"occurrence_id": "first"})
        assert _isolated_session.exists()

    def test_first_append_contains_single_entry(self, _isolated_session):
        """Após primeira chamada o arquivo deve ter exatamente 1 registro."""
        append_to_session({"occurrence_id": "only"})
        records = json.loads(_isolated_session.read_text(encoding="utf-8"))
        assert len(records) == 1
        assert records[0]["occurrence_id"] == "only"

    def test_consecutive_appends_accumulate_without_data_loss(self, _isolated_session):
        """Escritas consecutivas não devem perder entradas anteriores."""
        for i in range(5):
            append_to_session({"occurrence_id": f"id-{i}", "seq": i})

        records = json.loads(_isolated_session.read_text(encoding="utf-8"))
        assert len(records) == 5
        for i in range(5):
            assert records[i]["occurrence_id"] == f"id-{i}"
            assert records[i]["seq"] == i

    def test_atomic_write_uses_replace(self, _isolated_session, monkeypatch):
        """append_to_session deve usar os.replace para escrita atômica.

        Verifica que os.replace é chamado com um arquivo temporário no
        mesmo diretório e o caminho final SESSION_FILE como destino.
        """
        replace_calls: list[tuple[str, str]] = []
        original_replace = os.replace

        def spy_replace(src: str, dst: str) -> None:
            replace_calls.append((src, str(dst)))
            original_replace(src, dst)

        monkeypatch.setattr(os, "replace", spy_replace)

        append_to_session({"occurrence_id": "atomic-test"})

        assert len(replace_calls) == 1
        src, dst = replace_calls[0]
        # O arquivo temporário deve estar no mesmo diretório que SESSION_FILE
        assert Path(src).parent == Path(dst).parent
        # O destino deve ser o SESSION_FILE
        assert dst == str(session_module.SESSION_FILE)

    def test_file_is_valid_json_after_write(self, _isolated_session):
        """O arquivo resultante deve ser JSON válido após cada append."""
        for i in range(3):
            append_to_session({"occurrence_id": f"id-{i}"})
            content = _isolated_session.read_text(encoding="utf-8")
            data = json.loads(content)  # não deve lançar exceção
            assert isinstance(data, list)

    def test_append_to_corrupted_file_resets_cleanly(self, _isolated_session):
        """Append em arquivo corrompido deve descartar o conteúdo inválido
        e salvar apenas a nova entrada (comportamento de reinicialização)."""
        _isolated_session.write_text("{broken", encoding="utf-8")
        append_to_session({"occurrence_id": "new-entry"})
        records = json.loads(_isolated_session.read_text(encoding="utf-8"))
        assert len(records) == 1
        assert records[0]["occurrence_id"] == "new-entry"

    def test_tmp_file_not_left_behind_on_success(self, _isolated_session):
        """Nenhum arquivo .tmp deve permanecer no diretório após append bem-sucedido."""
        append_to_session({"occurrence_id": "clean"})
        tmp_files = list(_isolated_session.parent.glob(".session_tmp_*"))
        assert tmp_files == []


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------


class TestConstants:
    def test_recent_context_limit_is_positive_int(self):
        """RECENT_CONTEXT_LIMIT deve ser um inteiro positivo."""
        assert isinstance(RECENT_CONTEXT_LIMIT, int)
        assert RECENT_CONTEXT_LIMIT > 0

    def test_conversation_history_limit_is_positive_int(self):
        """CONVERSATION_HISTORY_LIMIT deve ser um inteiro positivo."""
        assert isinstance(CONVERSATION_HISTORY_LIMIT, int)
        assert CONVERSATION_HISTORY_LIMIT > 0

    def test_recent_context_limit_value(self):
        """RECENT_CONTEXT_LIMIT deve ser 10 conforme definido."""
        assert RECENT_CONTEXT_LIMIT == 10

    def test_conversation_history_limit_value(self):
        """CONVERSATION_HISTORY_LIMIT deve ser 6 conforme definido."""
        assert CONVERSATION_HISTORY_LIMIT == 6
