"""Testes de integração do fluxo principal do grafo LangGraph.

Todos os testes aqui executam o grafo completo via build_graph().invoke(),
mockando exclusivamente as dependências externas reais:
  - LLM (Ollama) — via patch em cada nó que chama get_llm()
  - Filesystem (reports/, session.json) — via monkeypatch + tmp_path
  - Prompt template — via patch em _load_prompt_template

Isso garante que o roteamento condicional, a passagem de estado entre nós
e a lógica de negócio sejam exercitados de ponta a ponta sem servidor externo.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from condominium_incident_agent.enums import Category, Severity
from condominium_incident_agent.graph import build_graph
from condominium_incident_agent.schemas import IncidentInput

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_TEMPLATE = (
    "Relato: {user_input}\n"
    "Por: {reported_by}\n"
    "Em: {reported_at}\n"
    "Contexto: {session_context}"
)


def _llm_response(
    category: str = "NOISE",
    severity: str = "LOW",
    apartment: str = "302",
    building: str = "A",
    summary: str = "Barulho excessivo reportado.",
    involved_people: list | None = None,
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
        "involved_people": involved_people or ["Morador"],
        "apartment": apartment,
        "building": building,
        "summary": summary,
    }
    return json.dumps(payload)


def _build_classify_llm_mock(response_text: str) -> MagicMock:
    """Monta o mock da cadeia llm.bind_tools().with_retry() para classify_incident."""
    ai_msg = AIMessage(content=response_text, tool_calls=[])
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = ai_msg

    mock_bound = MagicMock()
    mock_bound.with_retry.return_value = mock_chain

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_bound
    return mock_llm


def _build_validate_llm_mock(answer: str = "SINGLE") -> MagicMock:
    """Monta o mock do LLM para validate_input._detect_multiple_incidents."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content=answer)
    return mock_llm


def _make_config(reported_by: str = "Porteiro Silva") -> dict:
    thread_id = reported_by.strip().lower().replace(" ", "_")
    return {"configurable": {"thread_id": thread_id}}


def _initial_state(
    user_input: str = "Barulho excessivo no apartamento 302",
    reported_by: str = "Porteiro Silva",
) -> dict:
    incident = IncidentInput(user_input=user_input, reported_by=reported_by)
    return incident.to_initial_state()


# ---------------------------------------------------------------------------
# Fixture de contexto global para todos os testes
# ---------------------------------------------------------------------------

@pytest.fixture()
def patched_env(tmp_path, monkeypatch):
    """Configura o ambiente isolado para testes de integração.

    - Redireciona REPORTS_DIR e ESCALATED_DIR para tmp_path
    - Redireciona SESSION_FILE para tmp_path
    - Mocka _load_prompt_template para evitar leitura de disco
    """
    reports_dir = tmp_path / "reports"
    escalated_dir = reports_dir / "escalated"
    session_file = reports_dir / "session.json"

    monkeypatch.setattr(
        "condominium_incident_agent.nodes.save_occurrence.REPORTS_DIR", reports_dir
    )
    monkeypatch.setattr(
        "condominium_incident_agent.nodes.save_occurrence.ESCALATED_DIR", escalated_dir
    )

    import condominium_incident_agent.session as session_module
    monkeypatch.setattr(session_module, "SESSION_FILE", session_file)

    with patch(
        "condominium_incident_agent.nodes.prepare_context._load_prompt_template",
        return_value=_FAKE_TEMPLATE,
    ):
        yield {
            "reports_dir": reports_dir,
            "escalated_dir": escalated_dir,
            "session_file": session_file,
        }


# ---------------------------------------------------------------------------
# Cenário 1 — Ocorrência válida (fluxo feliz)
# ---------------------------------------------------------------------------

class TestHappyPath:
    def test_valid_occurrence_low_severity(self, patched_env):
        """Fluxo completo com ocorrência LOW deve salvar arquivo e preencher estado."""
        graph = build_graph()
        state = _initial_state()
        config = _make_config()

        with (
            patch(
                "condominium_incident_agent.nodes.validate_input.get_llm",
                return_value=_build_validate_llm_mock("SINGLE"),
            ),
            patch(
                "condominium_incident_agent.nodes.classify_incident.get_llm",
                return_value=_build_classify_llm_mock(_llm_response("NOISE", "LOW")),
            ),
        ):
            result = graph.invoke(state, config=config)

        assert result["category"] == Category.NOISE
        assert result["severity"] == Severity.LOW
        assert result["classification_error"] is None
        assert result["output_file"] is not None
        assert Path(result["output_file"]).exists()

    def test_valid_occurrence_file_content_correct(self, patched_env):
        """O arquivo JSON gerado deve conter todos os campos esperados."""
        graph = build_graph()
        state = _initial_state()
        config = _make_config()

        with (
            patch(
                "condominium_incident_agent.nodes.validate_input.get_llm",
                return_value=_build_validate_llm_mock("SINGLE"),
            ),
            patch(
                "condominium_incident_agent.nodes.classify_incident.get_llm",
                return_value=_build_classify_llm_mock(
                    _llm_response("MAINTENANCE", "MEDIUM", apartment="501", building="B")
                ),
            ),
        ):
            result = graph.invoke(state, config=config)

        data = json.loads(Path(result["output_file"]).read_text(encoding="utf-8"))
        assert data["category"] == "MAINTENANCE"
        assert data["severity"] == "MEDIUM"
        assert data["apartment"] == "501"
        assert data["building"] == "B"

    def test_occurrence_id_present_in_final_state(self, patched_env):
        """O estado final deve conter occurrence_id gerado."""
        graph = build_graph()
        state = _initial_state()
        config = _make_config()

        with (
            patch(
                "condominium_incident_agent.nodes.validate_input.get_llm",
                return_value=_build_validate_llm_mock("SINGLE"),
            ),
            patch(
                "condominium_incident_agent.nodes.classify_incident.get_llm",
                return_value=_build_classify_llm_mock(_llm_response()),
            ),
        ):
            result = graph.invoke(state, config=config)

        assert result["occurrence_id"] is not None
        assert len(result["occurrence_id"]) == 36


# ---------------------------------------------------------------------------
# Cenário 2 — Ocorrência crítica (HIGH severity)
# ---------------------------------------------------------------------------

class TestHighSeverityOccurrence:
    def test_high_severity_creates_escalated_file(self, patched_env):
        """Ocorrência HIGH deve gerar arquivo em reports/escalated/."""
        graph = build_graph()
        state = _initial_state(
            user_input="Invasão armada no lobby do bloco B, apartamento 401"
        )
        config = _make_config()

        with (
            patch(
                "condominium_incident_agent.nodes.validate_input.get_llm",
                return_value=_build_validate_llm_mock("SINGLE"),
            ),
            patch(
                "condominium_incident_agent.nodes.classify_incident.get_llm",
                return_value=_build_classify_llm_mock(
                    _llm_response("SECURITY", "HIGH", "401", "B")
                ),
            ),
        ):
            result = graph.invoke(state, config=config)

        assert result["escalated_file"] is not None
        assert Path(result["escalated_file"]).exists()

    def test_high_severity_escalated_file_has_escalated_flag(self, patched_env):
        """O arquivo escalated deve conter o campo escalated=True."""
        graph = build_graph()
        state = _initial_state(
            user_input="Invasão armada no lobby do bloco B"
        )
        config = _make_config()

        with (
            patch(
                "condominium_incident_agent.nodes.validate_input.get_llm",
                return_value=_build_validate_llm_mock("SINGLE"),
            ),
            patch(
                "condominium_incident_agent.nodes.classify_incident.get_llm",
                return_value=_build_classify_llm_mock(
                    _llm_response("SECURITY", "HIGH", "401", "B")
                ),
            ),
        ):
            result = graph.invoke(state, config=config)

        data = json.loads(Path(result["escalated_file"]).read_text(encoding="utf-8"))
        assert data["escalated"] is True
        assert "escalated_at" in data

    def test_high_severity_also_saves_main_report(self, patched_env):
        """Além do escalated, o relatório principal também deve ser salvo."""
        graph = build_graph()
        state = _initial_state(user_input="Incidente crítico de segurança")
        config = _make_config()

        with (
            patch(
                "condominium_incident_agent.nodes.validate_input.get_llm",
                return_value=_build_validate_llm_mock("SINGLE"),
            ),
            patch(
                "condominium_incident_agent.nodes.classify_incident.get_llm",
                return_value=_build_classify_llm_mock(
                    _llm_response("SECURITY", "HIGH")
                ),
            ),
        ):
            result = graph.invoke(state, config=config)

        assert result["output_file"] is not None
        assert Path(result["output_file"]).exists()


# ---------------------------------------------------------------------------
# Cenário 3 — Entrada inválida (múltiplos incidentes)
# ---------------------------------------------------------------------------

class TestMultipleIncidentsRejection:
    def test_multiple_incidents_sets_flag(self, patched_env):
        """LLM detectando MULTIPLE deve marcar multiple_incidents_detected=True."""
        graph = build_graph()
        state = _initial_state(
            user_input="Barulho no 302 e também uma encomenda perdida do 501"
        )
        config = _make_config()

        with patch(
            "condominium_incident_agent.nodes.validate_input.get_llm",
            return_value=_build_validate_llm_mock("MULTIPLE"),
        ):
            result = graph.invoke(state, config=config)

        assert result["multiple_incidents_detected"] is True

    def test_multiple_incidents_does_not_save_file(self, patched_env):
        """Relato com múltiplos incidentes não deve gerar arquivo de ocorrência."""
        graph = build_graph()
        state = _initial_state(
            user_input="Barulho no 302 e também uma encomenda perdida do 501"
        )
        config = _make_config()

        with patch(
            "condominium_incident_agent.nodes.validate_input.get_llm",
            return_value=_build_validate_llm_mock("MULTIPLE"),
        ):
            result = graph.invoke(state, config=config)

        assert result["output_file"] is None
        assert result["category"] is None

    def test_multiple_incidents_no_classify_called(self, patched_env):
        """classify_incident não deve ser chamado quando múltiplos incidentes detectados."""
        graph = build_graph()
        state = _initial_state(
            user_input="Dois eventos distintos aqui"
        )
        config = _make_config()

        mock_classify_llm = _build_classify_llm_mock(_llm_response())

        with (
            patch(
                "condominium_incident_agent.nodes.validate_input.get_llm",
                return_value=_build_validate_llm_mock("MULTIPLE"),
            ),
            patch(
                "condominium_incident_agent.nodes.classify_incident.get_llm",
                return_value=mock_classify_llm,
            ),
        ):
            graph.invoke(state, config=config)

        # classify_incident não deve ter sido invocado
        mock_classify_llm.bind_tools.assert_not_called()


# ---------------------------------------------------------------------------
# Cenário 4 — Falha de classificação (LLM retorna texto sem JSON)
# ---------------------------------------------------------------------------

class TestClassificationFailure:
    def test_invalid_llm_response_sets_classification_error(self, patched_env):
        """Resposta inválida do LLM deve preencher classification_error."""
        graph = build_graph()
        state = _initial_state()
        config = _make_config()

        with (
            patch(
                "condominium_incident_agent.nodes.validate_input.get_llm",
                return_value=_build_validate_llm_mock("SINGLE"),
            ),
            patch(
                "condominium_incident_agent.nodes.classify_incident.get_llm",
                return_value=_build_classify_llm_mock(
                    "Desculpe, não consegui classificar este incidente."
                ),
            ),
        ):
            result = graph.invoke(state, config=config)

        assert result["classification_error"] is not None

    def test_classification_failure_does_not_save_file(self, patched_env):
        """Falha de classificação não deve gerar arquivo de ocorrência."""
        graph = build_graph()
        state = _initial_state()
        config = _make_config()

        with (
            patch(
                "condominium_incident_agent.nodes.validate_input.get_llm",
                return_value=_build_validate_llm_mock("SINGLE"),
            ),
            patch(
                "condominium_incident_agent.nodes.classify_incident.get_llm",
                return_value=_build_classify_llm_mock("Texto sem JSON"),
            ),
        ):
            result = graph.invoke(state, config=config)

        assert result["output_file"] is None

    def test_classification_failure_category_and_severity_are_none(self, patched_env):
        """Em caso de falha, category e severity devem permanecer None."""
        graph = build_graph()
        state = _initial_state()
        config = _make_config()

        with (
            patch(
                "condominium_incident_agent.nodes.validate_input.get_llm",
                return_value=_build_validate_llm_mock("SINGLE"),
            ),
            patch(
                "condominium_incident_agent.nodes.classify_incident.get_llm",
                return_value=_build_classify_llm_mock("resposta inválida"),
            ),
        ):
            result = graph.invoke(state, config=config)

        assert result["category"] is None
        assert result["severity"] is None


# ---------------------------------------------------------------------------
# Cenário 5 — Uso de histórico (session_history refletido no estado)
# ---------------------------------------------------------------------------

class TestSessionHistoryUsage:
    def test_session_history_updated_after_successful_occurrence(self, patched_env):
        """session_history deve conter a nova ocorrência após processamento."""
        graph = build_graph()
        state = _initial_state()
        config = _make_config()

        with (
            patch(
                "condominium_incident_agent.nodes.validate_input.get_llm",
                return_value=_build_validate_llm_mock("SINGLE"),
            ),
            patch(
                "condominium_incident_agent.nodes.classify_incident.get_llm",
                return_value=_build_classify_llm_mock(_llm_response("NOISE", "LOW")),
            ),
        ):
            result = graph.invoke(state, config=config)

        assert len(result["session_history"]) == 1
        entry = result["session_history"][0]
        assert entry["category"] == "NOISE"
        assert entry["severity"] == "LOW"

    def test_session_history_empty_on_classification_failure(self, patched_env):
        """session_history não deve ser atualizado em caso de falha de classificação."""
        graph = build_graph()
        state = _initial_state()
        config = _make_config()

        with (
            patch(
                "condominium_incident_agent.nodes.validate_input.get_llm",
                return_value=_build_validate_llm_mock("SINGLE"),
            ),
            patch(
                "condominium_incident_agent.nodes.classify_incident.get_llm",
                return_value=_build_classify_llm_mock("texto sem json"),
            ),
        ):
            result = graph.invoke(state, config=config)

        assert result["session_history"] == []

    def test_prepare_context_sees_existing_session_records(self, patched_env):
        """prepare_context deve ler registros existentes no session.json."""
        # Popula session.json antes de invocar o grafo
        session_file = patched_env["session_file"]
        session_file.parent.mkdir(parents=True, exist_ok=True)
        existing = [
            {
                "occurrence_id": "old-uuid",
                "category": "NOISE",
                "severity": "LOW",
                "apartment": "302",
                "building": "A",
                "summary": "ocorrência anterior",
            }
        ]
        session_file.write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")

        graph = build_graph()
        state = _initial_state()
        config = _make_config()

        with (
            patch(
                "condominium_incident_agent.nodes.validate_input.get_llm",
                return_value=_build_validate_llm_mock("SINGLE"),
            ),
            patch(
                "condominium_incident_agent.nodes.classify_incident.get_llm",
                return_value=_build_classify_llm_mock(_llm_response("NOISE", "MEDIUM")),
            ),
        ):
            result = graph.invoke(state, config=config)

        # A nova ocorrência deve ter sido salva
        assert result["output_file"] is not None
        # O session.json agora deve ter 2 registros
        records = json.loads(session_file.read_text(encoding="utf-8"))
        assert len(records) == 2


# ---------------------------------------------------------------------------
# Cenário 6 — Persistência (session.json atualizado)
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_session_json_written_after_successful_occurrence(self, patched_env):
        """session.json deve ser atualizado com a entrada da ocorrência processada."""
        graph = build_graph()
        state = _initial_state()
        config = _make_config()
        session_file = patched_env["session_file"]

        with (
            patch(
                "condominium_incident_agent.nodes.validate_input.get_llm",
                return_value=_build_validate_llm_mock("SINGLE"),
            ),
            patch(
                "condominium_incident_agent.nodes.classify_incident.get_llm",
                return_value=_build_classify_llm_mock(_llm_response("ACCESS", "MEDIUM")),
            ),
        ):
            graph.invoke(state, config=config)

        assert session_file.exists()
        records = json.loads(session_file.read_text(encoding="utf-8"))
        assert len(records) == 1
        assert records[0]["category"] == "ACCESS"

    def test_session_json_not_written_on_failure(self, patched_env):
        """session.json não deve ser modificado quando a classificação falha."""
        graph = build_graph()
        state = _initial_state()
        config = _make_config()
        session_file = patched_env["session_file"]

        with (
            patch(
                "condominium_incident_agent.nodes.validate_input.get_llm",
                return_value=_build_validate_llm_mock("SINGLE"),
            ),
            patch(
                "condominium_incident_agent.nodes.classify_incident.get_llm",
                return_value=_build_classify_llm_mock("texto inválido"),
            ),
        ):
            graph.invoke(state, config=config)

        # Arquivo não deve existir ou estar vazio
        assert not session_file.exists() or session_file.read_text() == ""

    def test_json_report_contains_reported_by_and_at(self, patched_env):
        """O arquivo de relatório deve conter reported_by e reported_at."""
        graph = build_graph()
        state = _initial_state(reported_by="Porteiro Carlos")
        config = _make_config("Porteiro Carlos")

        with (
            patch(
                "condominium_incident_agent.nodes.validate_input.get_llm",
                return_value=_build_validate_llm_mock("SINGLE"),
            ),
            patch(
                "condominium_incident_agent.nodes.classify_incident.get_llm",
                return_value=_build_classify_llm_mock(_llm_response()),
            ),
        ):
            result = graph.invoke(state, config=config)

        data = json.loads(Path(result["output_file"]).read_text(encoding="utf-8"))
        assert data["reported_by"] == "Porteiro Carlos"
        assert data["reported_at"] is not None
