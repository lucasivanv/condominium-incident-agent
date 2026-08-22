from condominium_incident_agent.llm import get_llm


def test_ollama_connection():
    llm = get_llm()

    response = llm.invoke("Responda apenas: OK")

    assert response.content