"""Ponto de entrada do agente de classificação de incidentes."""

import json
import logging
import sys
from pathlib import Path

from pydantic import ValidationError

from incident_classification_agent.graph import build_graph
from incident_classification_agent.schemas import IncidentInput

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

logger = logging.getLogger(__name__)


def _load_input(path: str) -> IncidentInput:
    """Lê e valida o arquivo JSON de entrada usando o schema Pydantic.

    Args:
        path: Caminho para o arquivo JSON.

    Returns:
        Instância validada de IncidentInput.

    Raises:
        FileNotFoundError: Se o arquivo não existir.
        ValueError: Se o JSON for inválido ou não atender ao schema.
    """
    filepath = Path(path)

    if not filepath.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")

    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON inválido: {exc}") from exc

    try:
        return IncidentInput(**data)
    except ValidationError as exc:
        # Formata os erros do Pydantic de forma legível para o usuário
        errors = "; ".join(
            f"{' > '.join(str(loc) for loc in err['loc'])}: {err['msg']}"
            for err in exc.errors()
        )
        raise ValueError(f"Input inválido — {errors}") from exc


def main() -> None:
    """Inicializa o grafo e processa o incidente a partir de um arquivo JSON.

    O thread_id é derivado do campo reported_by, garantindo que o histórico
    de estado do checkpointer seja isolado por quem reporta os incidentes.

    Uso:
        python -m incident_classification_agent.main <caminho/para/input.json>

    Exemplo:
        python -m incident_classification_agent.main examples/input.json
    """
    if len(sys.argv) != 2:
        print(
            "Uso: python -m incident_classification_agent.main <caminho/para/input.json>"
        )
        print(
            "Exemplo: python -m incident_classification_agent.main examples/input.json"
        )
        sys.exit(1)

    try:
        incident_input = _load_input(sys.argv[1])
    except (FileNotFoundError, ValueError) as exc:
        print(f"\n❌ Erro ao carregar input: {exc}")
        sys.exit(1)

    initial_state = incident_input.to_initial_state()
    graph = build_graph()

    # thread_id idealmente seria derivado do apartamento para que o histórico
    # de estado do checkpointer reflita reincidências por unidade habitacional.
    # Como o apartamento só é conhecido após a classificação (processamento do
    # LLM), usamos reported_by como identificador de sessão — limitação conhecida:
    # porteiros diferentes reportando o mesmo apartamento ficam em threads distintas.
    # O session.json é a fonte de verdade para reincidência, independente do thread_id.
    thread_id = incident_input.reported_by.strip().lower().replace(" ", "_")
    config = {"configurable": {"thread_id": thread_id}}

    print("\n⏳ Processando...\n")
    logger.info("Starting incident classification agent — thread_id: %s", thread_id)

    final_state = graph.invoke(initial_state, config=config)

    logger.info("Agent finished — output_file: %s", final_state.get("output_file"))


if __name__ == "__main__":
    main()
