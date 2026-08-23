# Estratégia de Testes — condominium-incident-agent

## Visão Geral

O projeto utiliza **pytest** como framework de testes, organizado em duas camadas:

```
tests/
├── test_schemas.py          # testes de schema e enums (pré-existente)
├── unit/                    # testes unitários por componente
│   ├── test_validate_input.py
│   ├── test_prepare_context.py
│   ├── test_classify_incident.py
│   ├── test_generate_response.py
│   ├── test_save_occurrence.py
│   ├── test_handle_error.py
│   ├── test_session.py
│   ├── test_lookup_resident.py
│   └── test_get_session_history.py
└── integration/
    └── test_graph_flow.py   # fluxo completo ponta a ponta
```

---

## Tipos de Teste

### Testes Unitários

Testam cada componente de forma isolada, sem dependências externas reais.
Usam `unittest.mock.patch` para substituir:

- **LLM (Ollama)** — mockado nos pontos de injeção `get_llm()` de cada nó
- **Filesystem** — redirecionado para `tmp_path` do pytest via `monkeypatch.setattr`
- **session.json** — `load_session` e `append_to_session` mockados ou redirecionados
- **residents.json** — `_load_residents` mockado com fixtures internas

| Arquivo | Componente | Foco |
|---|---|---|
| `test_validate_input.py` | Nó `validate_input` | Validação de campos, geração de UUID, detecção de múltiplos incidentes, fallback de LLM |
| `test_prepare_context.py` | Nó `prepare_context` | Substituição de variáveis no template, construção do contexto de sessão |
| `test_classify_incident.py` | Nó `classify_incident` | Parse de JSON, validação de enums, loop agentic, roteamento pós-classificação |
| `test_generate_response.py` | Nó `generate_response` | Formatação de mensagens de sucesso, erro e múltiplos incidentes |
| `test_save_occurrence.py` | Nó `save_occurrence` | Criação de arquivos, lógica de escalamento HIGH, atualização do session_history |
| `test_handle_error.py` | Nó `handle_error` | Passagem de estado sem alteração |
| `test_session.py` | Módulo `session` | Leitura e escrita do session.json, resiliência a falhas |
| `test_lookup_resident.py` | Tool `lookup_resident` | Busca case-insensitive, filtro por bloco, retorno de dados completos |
| `test_get_session_history.py` | Tool `get_session_history` | Filtragem por apartamento/bloco, contagem, campos do retorno |

### Testes de Integração

Localizados em `tests/integration/test_graph_flow.py`, executam o grafo LangGraph completo via `build_graph().invoke()` com todas as dependências externas mockadas. Cobrem o fluxo de ponta a ponta — da entrada do usuário até a persistência no disco — verificando roteamento condicional, passagem de estado entre nós e comportamento observável em cada cenário relevante.

---

## Cenários Cobertos

### Ocorrência Válida
- Fluxo completo com severidade LOW e MEDIUM
- Campos do arquivo JSON gerado validados (category, severity, apartment, etc.)
- occurrence_id presente no estado final

### Ocorrência Crítica (HIGH)
- Arquivo criado em `reports/escalated/` com flag `escalated: true`
- Relatório principal também salvo normalmente

### Entrada Inválida — Múltiplos Incidentes
- LLM detecta MULTIPLE → `multiple_incidents_detected=True`
- Fluxo encurta para `generate_response` sem chamar `classify_incident`
- Nenhum arquivo de ocorrência criado, `category` permanece `None`

### Falha de Dependência — LLM sem JSON válido
- Resposta inválida do LLM → `classification_error` preenchido
- Roteamento para `handle_error` → `generate_response`
- Sem arquivo persistido, sem entrada no session.json

### Uso de Histórico
- `session_history` atualizado em memória após ocorrência bem-sucedida
- `prepare_context` lê registros existentes no session.json
- Após falha de classificação, session_history permanece vazio

### Persistência
- `session.json` gravado após ocorrência bem-sucedida
- `session.json` não modificado após falha de classificação
- Arquivo de relatório contém `reported_by` e `reported_at`

---

## Estratégia de Mock

### LLM
```python
# validate_input
with patch("condominium_incident_agent.nodes.validate_input.get_llm",
           return_value=mock_llm_returning("SINGLE")):
    ...

# classify_incident
mock_llm.bind_tools.return_value.with_retry.return_value.invoke.return_value = AIMessage(...)
with patch("condominium_incident_agent.nodes.classify_incident.get_llm",
           return_value=mock_llm):
    ...
```

### Filesystem
```python
# Redireciona diretórios de relatórios para tmp_path
monkeypatch.setattr("condominium_incident_agent.nodes.save_occurrence.REPORTS_DIR", tmp_path)
monkeypatch.setattr("condominium_incident_agent.session.SESSION_FILE", tmp_path / "session.json")
```

### Tools
```python
# Mock direto da função de carregamento de dados
with patch("condominium_incident_agent.tools.lookup_resident._load_residents",
           return_value=[...]):
    ...
```

---

## Como Executar

```bash
# Todos os testes
uv run pytest

# Somente unitários
uv run pytest tests/unit/

# Somente integração
uv run pytest tests/integration/

# Com cobertura (requer pytest-cov)
uv run pytest --cov=src/condominium_incident_agent

# Verboso
uv run pytest -v
```

---

## Premissas

- Nenhum teste requer Ollama rodando — o LLM é sempre mockado
- Nenhum teste escreve no filesystem real do projeto — todo I/O usa `tmp_path`
- Os testes são independentes entre si e podem ser executados em qualquer ordem
- O `test_schemas.py` pré-existente cobre `IncidentInput` e os enums — não duplicado
