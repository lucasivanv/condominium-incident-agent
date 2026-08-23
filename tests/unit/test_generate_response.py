"""Testes unitários para o nó generate_response."""

from condominium_incident_agent.enums import Category, Severity
from condominium_incident_agent.nodes.generate_response import (
    generate_response,
    _format_success,
    _format_error,
    _format_multiple_incidents,
)


def _make_success_state(**kwargs) -> dict:
    """Estado base para o caminho feliz."""
    base = {
        "occurrence_id": "test-uuid-001",
        "user_input": "Barulho excessivo no corredor",
        "reported_by": "Porteiro Silva",
        "reported_at": "2026-07-14T22:00:00Z",
        "category": Category.NOISE,
        "severity": Severity.LOW,
        "involved_people": ["João"],
        "apartment": "302",
        "building": "A",
        "summary": "Relato de barulho excessivo no corredor do bloco A.",
        "output_file": "/reports/20260714_test-uuid-001.json",
        "escalated_file": None,
        "classification_error": None,
        "resident_info": None,
        "multiple_incidents_detected": False,
        "conversation_history": [],
        "session_history": [],
    }
    base.update(kwargs)
    return base


class TestGenerateResponse:
    def test_success_path_updates_conversation_history(self):
        """A resposta deve ser adicionada ao conversation_history."""
        state = _make_success_state()
        result = generate_response(state)

        assert len(result["conversation_history"]) == 1

    def test_success_path_response_contains_occurrence_id(self, capsys):
        """A resposta de sucesso deve conter o ID da ocorrência."""
        state = _make_success_state()
        generate_response(state)
        captured = capsys.readouterr()
        assert "test-uuid-001" in captured.out

    def test_success_path_response_contains_category(self, capsys):
        """A resposta de sucesso deve mencionar a categoria."""
        state = _make_success_state(category=Category.SECURITY)
        generate_response(state)
        captured = capsys.readouterr()
        assert "SECURITY" in captured.out

    def test_success_path_response_contains_severity(self, capsys):
        """A resposta de sucesso deve mencionar a severidade."""
        state = _make_success_state(severity=Severity.HIGH)
        generate_response(state)
        captured = capsys.readouterr()
        assert "HIGH" in captured.out

    def test_error_path_when_classification_error_set(self, capsys):
        """Estado com classification_error deve gerar resposta de erro."""
        state = _make_success_state(
            classification_error="Campo 'category' ausente.",
            category=None,
            severity=None,
        )
        result = generate_response(state)
        captured = capsys.readouterr()
        assert "❌" in captured.out or "Não foi possível classificar" in captured.out
        assert len(result["conversation_history"]) == 1

    def test_multiple_incidents_path(self, capsys):
        """Estado com multiple_incidents_detected deve gerar resposta adequada."""
        state = _make_success_state(
            multiple_incidents_detected=True,
            category=None,
            severity=None,
        )
        generate_response(state)
        captured = capsys.readouterr()
        assert "Múltiplos incidentes" in captured.out

    def test_high_severity_with_escalated_file_mentioned(self, capsys):
        """Ocorrência HIGH com escalated_file deve mencionar escalonamento."""
        state = _make_success_state(
            severity=Severity.HIGH,
            escalated_file="/reports/escalated/20260714_test-uuid-001.json",
        )
        generate_response(state)
        captured = capsys.readouterr()
        assert "ESCALONADO" in captured.out or "escalated" in captured.out.lower()

    def test_resident_info_included_when_found(self, capsys):
        """Dados do morador devem aparecer na resposta quando encontrado."""
        state = _make_success_state(
            resident_info={
                "found": True,
                "resident_name": "Maria Oliveira",
                "authorized_visitors": ["Carlos"],
            }
        )
        generate_response(state)
        captured = capsys.readouterr()
        assert "Maria Oliveira" in captured.out

    def test_no_resident_info_when_not_found(self, capsys):
        """Quando morador não encontrado, não deve aparecer na resposta."""
        state = _make_success_state(
            resident_info={"found": False}
        )
        generate_response(state)
        captured = capsys.readouterr()
        # Não deve mencionar nome de morador
        assert "Morador cadastrado" not in captured.out

    def test_output_file_path_in_success_response(self, capsys):
        """O caminho do arquivo salvo deve aparecer na resposta de sucesso."""
        state = _make_success_state(output_file="/reports/file.json")
        generate_response(state)
        captured = capsys.readouterr()
        assert "/reports/file.json" in captured.out

    def test_existing_history_is_preserved(self):
        """Histórico existente não deve ser apagado."""
        state = _make_success_state(conversation_history=["mensagem anterior"])
        result = generate_response(state)
        assert result["conversation_history"][0] == "mensagem anterior"
        assert len(result["conversation_history"]) == 2


class TestFormatSuccess:
    def test_contains_occurrence_id(self):
        state = _make_success_state()
        msg = _format_success(state)
        assert "test-uuid-001" in msg

    def test_contains_category_value(self):
        state = _make_success_state(category=Category.ACCESS)
        msg = _format_success(state)
        assert "ACCESS" in msg

    def test_contains_severity_value(self):
        state = _make_success_state(severity=Severity.MEDIUM)
        msg = _format_success(state)
        assert "MEDIUM" in msg

    def test_apartment_and_building_shown(self):
        state = _make_success_state(apartment="502", building="B")
        msg = _format_success(state)
        assert "502" in msg
        assert "B" in msg

    def test_no_apartment_section_when_absent(self):
        state = _make_success_state(apartment=None, building=None)
        msg = _format_success(state)
        assert "Apartamento" not in msg


class TestFormatError:
    def test_contains_error_reason(self):
        state = _make_success_state(
            classification_error="Campo 'severity' ausente.",
            category=None,
            severity=None,
        )
        msg = _format_error(state)
        assert "Campo 'severity' ausente." in msg

    def test_contains_occurrence_id(self):
        state = _make_success_state(
            classification_error="erro",
            category=None,
            severity=None,
        )
        msg = _format_error(state)
        assert "test-uuid-001" in msg


class TestFormatMultipleIncidents:
    def test_contains_multiple_incidents_message(self):
        state = _make_success_state(multiple_incidents_detected=True)
        msg = _format_multiple_incidents(state)
        assert "Múltiplos incidentes" in msg

    def test_contains_occurrence_id(self):
        state = _make_success_state(
            occurrence_id="multi-uuid-001",
            multiple_incidents_detected=True,
        )
        msg = _format_multiple_incidents(state)
        assert "multi-uuid-001" in msg
