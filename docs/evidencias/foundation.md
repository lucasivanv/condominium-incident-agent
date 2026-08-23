# Foundation — Condominium Incident Agent

**Data da auditoria:** 2026-08-22
**Ambiente:** Windows 11, Python 3.12.13, uv, pytest 9.1.1

---

## 1. Funcionalidades Existentes

| Funcionalidade                                  | Arquivo principal                                 | Status         |
| ----------------------------------------------- | ------------------------------------------------- | -------------- |
| Validação de entrada com Pydantic               | `schemas.py`, `nodes/validate_input.py`           | ✅ Operacional |
| Detecção de múltiplos incidentes via LLM        | `nodes/validate_input.py`                         | ✅ Operacional |
| Consulta ao cadastro de moradores               | `tools/lookup_resident.py`, `data/residents.json` | ✅ Operacional |
| Consulta ao histórico da sessão                 | `tools/get_session_history.py`, `session.py`      | ✅ Operacional |
| Classificação de categoria e severidade via LLM | `nodes/classify_incident.py`                      | ✅ Operacional |
| Loop agentic com tool calling (até 5 iterações) | `nodes/classify_incident.py`                      | ✅ Operacional |
| Elevação de severidade por reincidência         | `prompts/classifier.md`                           | ✅ Operacional |
| Persistência da ocorrência em disco (JSON)      | `nodes/save_occurrence.py`                        | ✅ Operacional |
| Escalonamento automático de ocorrências HIGH    | `nodes/save_occurrence.py`                        | ✅ Operacional |
| Atualização do histórico de sessão em disco     | `session.py`                                      | ✅ Operacional |
| Histórico de estado em memória via MemorySaver  | `graph.py`                                        | ✅ Operacional |
| Geração de resposta formatada ao usuário        | `nodes/generate_response.py`                      | ✅ Operacional |
| Tratamento de erros de classificação            | `nodes/handle_error.py`                           | ✅ Operacional |
| Fluxo condicional (múltiplos incidentes, erro)  | `graph.py`                                        | ✅ Operacional |
| Retry automático no LLM (até 3 tentativas)      | `llm.py`, `nodes/classify_incident.py`            | ✅ Operacional |
| Configuração por variável de ambiente           | `llm.py`, `.env.example`                          | ✅ Operacional |

---

## 2. Problemas Encontrados

### P1 — Docstring incorreta em `classify_incident.py`

A docstring declarava que o LLM recebia as tools `lookup_resident` e `save_occurrence`. A lista real é `[lookup_resident, get_session_history]`. A tool `save_occurrence` nunca foi exposta ao LLM neste nó.

### P2 — `_build_session_context` sempre retornava contexto vazio

A função filtrava o histórico por `state.get("apartment")`, que é sempre `None` nesse ponto do fluxo — o apartamento só é extraído pelo LLM em `classify_incident`, que ocorre após `prepare_context`. O placeholder `{session_context}` recebia sempre "nenhuma ocorrência anterior" mesmo com histórico existente.

### P3 — `_detect_multiple_incidents` sem tratamento de exceção

Qualquer falha na chamada ao LLM (timeout, modelo indisponível, erro de rede) propagava como exceção não capturada, derrubando o grafo inteiro sem gerar resposta ao usuário.

### P4 — `pyproject.toml` sem `testpaths`

Sem `[tool.pytest.ini_options]`, o pytest varria o diretório raiz para coletar testes, podendo coletar módulos de `src/` acidentalmente em projetos com layout `src/`.

### P5 — Loop agentic sem log de esgotamento

O `for _ in range(5)` não tinha cláusula `else`. O esgotamento das 5 iterações sem resposta final passava silenciosamente, dificultando o diagnóstico quando ocorria.

### P6 — Tabela de ferramentas no README inconsistente com o código

A tabela descrevia `save_occurrence` como exposta ao LLM em `classify_incident`, contradizendo o código e a própria seção de Decisões de Projeto do README.

### P7 — Categoria e severidade exibidas com prefixo de enum

Identificado na execução real: a resposta ao usuário exibia `Category.ACCESS` e `Severity.LOW` em vez de `ACCESS` e `LOW`, porque `generate_response.py` usava o objeto enum diretamente sem chamar `.value`.

---

## 3. Correções Realizadas

| Arquivo                      | Correção                                                                                                  |
| ---------------------------- | --------------------------------------------------------------------------------------------------------- |
| `nodes/classify_incident.py` | Docstring corrigida; `import re` removido; cláusula `for/else` adicionada ao loop agentic                 |
| `nodes/prepare_context.py`   | `_build_session_context` reescrita para informar total da sessão sem filtrar por apartamento              |
| `nodes/validate_input.py`    | `try/except` adicionado em `_detect_multiple_incidents` com fallback conservador (assume incidente único) |
| `nodes/generate_response.py` | Categoria e severidade exibidas via `.value` dos enums                                                    |
| `pyproject.toml`             | Adicionado `[tool.pytest.ini_options]` com `testpaths = ["tests"]`                                        |
| `README.md`                  | Tabela de ferramentas corrigida — `save_occurrence` descrita como não exposta ao LLM                      |

---

## 4. Testes e Execução Após Correções

### pytest

```
uv run pytest tests/test_llm.py -vv -s

collected 1 item
tests/test_llm.py::test_ollama_connection PASSED

1 passed in 0.66s
```

### Execução da aplicação (2ª execução — com histórico de sessão)

```
uv run python -m condominium_incident_agent.main examples/input.json

⏳ Processando...

✅ Ocorrência registrada com sucesso.

🆔 ID: 2c54e3f8-9101-4666-b5b7-d2ec2c71ccdb
📁 Categoria: ACCESS
⚠️  Severidade: MEDIUM
🏠 Apartamento: 101
🏢 Bloco: A
👥 Envolvidos: Ana Mendes, Carlos Mendes
🔍 Morador cadastrado: Carlos Mendes
   Visitantes autorizados: Ana Mendes, Roberto Mendes

📝 Resumo: Severidade elevada para MEDIUM devido a reincidência: primeira ocorrência de ACCESS registrada para este apartamento.

💾 Arquivo salvo em: C:\dev\condominium-incident-agent\reports\20260822T212418Z_2c54e3f8-9101-4666-b5b7-d2ec2c71ccdb.json
```

Fluxo completo executado: `validate_input` → `prepare_context` → `classify_incident` (3 chamadas ao LLM com tool calls) → `save_occurrence` → `generate_response`. Reincidência detectada corretamente (LOW → MEDIUM).

---

## 5. Limitações Remanescentes

| #   | Limitação                                                                                                      | Localização             | Documentada? |
| --- | -------------------------------------------------------------------------------------------------------------- | ----------------------- | ------------ |
| L1  | `session.json` sem escrita atômica — risco de condição de corrida em execuções paralelas                       | `session.py`            | ✅           |
| L2  | `thread_id` baseado em `reported_by` — porteiros distintos para o mesmo apartamento ficam em threads separados | `main.py`               | ✅           |
| L3  | `MemorySaver` é volátil — histórico em memória perdido ao encerrar o processo                                  | `graph.py`              | ✅           |
| L4  | Único teste depende do Ollama em execução — trava o pytest sem o serviço disponível                            | `tests/test_llm.py`     | Parcial      |
| L5  | Sem suíte de testes unitários com mocks                                                                        | `tests/`                | Não          |
| L6  | Resumo pode ser gerado em inglês pelo `qwen2.5:7b` — comportamento não determinístico do modelo                | `prompts/classifier.md` | Não          |
