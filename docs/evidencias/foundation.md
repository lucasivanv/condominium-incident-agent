# Foundation — Condominium Incident Agent

**Data da auditoria inicial:** 2026-08-22
**Data da revisão:** 2026-08-27
**Ambiente:** Windows 11, Python 3.12.13, uv e pytest 9.1.1

## 1. Objetivo

Registrar o estado inicial herdado do projeto do módulo anterior, os problemas encontrados na estabilização do fork e a evolução do baseline até a arquitetura atual. Resultados da auditoria inicial são identificados como históricos e não devem ser interpretados como limitações ainda existentes.

## 2. Capacidades preservadas e evoluídas

| Capacidade | Implementação principal | Estado atual |
| --- | --- | --- |
| Validação de entrada com Pydantic | `schemas.py`, `nodes/validate_input.py` | Operacional |
| Detecção de múltiplos incidentes | `nodes/validate_input.py` | Operacional, com fallback controlado |
| Consulta ao cadastro de moradores | `tools/lookup_resident.py` | Operacional e restrita por allowlist |
| Consulta ao histórico de ocorrências | `tools/get_session_history.py`, `session.py` | Operacional e limitada |
| Classificação via LLM | `nodes/classify_incident.py` | Operacional, com schema e enums validados |
| Loop agentic | `nodes/classify_incident.py` | Limitado a cinco iterações |
| Reincidência e elevação de severidade | `prompts/classifier.md` | Operacional |
| Memória e recuperação contextual | `graph.py`, `nodes/prepare_context.py` | Fan-out/fan-in e contexto limitado |
| Persistência da ocorrência | `nodes/save_occurrence.py`, `session.py` | Escritas individuais atômicas |
| Ações críticas `HIGH` | `security.py`, `nodes/save_occurrence.py` | Condicionadas à aprovação humana válida |
| Observabilidade | `observability.py` | Logs e auditoria correlacionados |
| Automação low-code | `nodes/send_to_flowise.py`, `tools/flowise_webhook.py` | POST resiliente após autorização |
| Resposta ao usuário | `nodes/generate_response.py` | Sanitizada e com minimização de dados |
| CI e análise de risco | `.github/workflows/ci.yml`, `ci_analysis.py` | Lint, testes, build, anomalias e quality gate |

## 3. Problemas encontrados no baseline

### P1 — Documentação das tools inconsistente

A docstring do classificador e o README original indicavam que `save_occurrence` era exposta ao LLM. O código utilizava somente `lookup_resident` e `get_session_history`. A documentação foi corrigida e a arquitetura atual mantém exclusivamente tools de leitura disponíveis ao modelo.

### P2 — Recuperação contextual vazia

O contexto era filtrado por `state.get("apartment")` antes de o apartamento ser classificado, fazendo com que o histórico pré-carregado permanecesse vazio. A recuperação passou a extrair uma indicação de apartamento do relato e posteriormente foi separada em dois ramos independentes de contexto.

### P3 — Falha não tratada na detecção auxiliar

Timeout, indisponibilidade do modelo ou erro de rede na detecção de múltiplos incidentes encerravam o grafo por exceção. A etapa recebeu tratamento controlado e fallback conservador para incidente único.

### P4 — Coleta de testes sem diretório definido

O `pyproject.toml` não declarava `testpaths`, permitindo que o pytest percorresse áreas desnecessárias do projeto. A configuração passou a limitar a coleta a `tests/`.

### P5 — Esgotamento silencioso do loop agentic

O loop de cinco iterações não diferenciava uma resposta final de seu esgotamento. A cláusula de parada passou a gerar erro controlado quando o modelo não conclui a classificação.

### P6 — Exibição incorreta dos enums

A resposta apresentava `Category.ACCESS` e `Severity.LOW`. `generate_response` passou a usar os valores `ACCESS` e `LOW`.

## 4. Correções e refinamentos posteriores

| Área | Alteração | Evidência relacionada |
| --- | --- | --- |
| Testes | Suíte unitária com mocks e integração pelo grafo completo | `test-strategy.md` |
| Memória | Recuperação contextual limitada e paralela | `memory.md`, `architecture.md` |
| Resiliência | Timeout, retry seletivo, fallback e escrita atômica | `resilience.md` |
| Segurança | Aprovação HMAC, allowlist e bloqueio determinístico | `security.md` |
| Hardening | Separação `SystemMessage`/`HumanMessage` e sanitização | `prompts-model-refinement.md` |
| Observabilidade | Logs estruturados e auditoria por `correlation_id` | `observability.md` |
| Low-code | Triagem Flowise integrada após persistência autorizada | `low-code.md` |
| DevOps | CI, JUnit, build, artifacts, anomalia e risco | `devops-qa.md` |

## 5. Validação

Na auditoria inicial, um teste de conectividade com Ollama e uma execução manual confirmaram o funcionamento básico do fork. Esse teste dependente do serviço real foi posteriormente removido da estratégia automatizada: a suíte atual usa mocks para Ollama e integrações externas, evitando travamento quando os serviços locais não estão ativos.

Comandos atuais de reprodução:

```bash
# Suíte completa
uv run pytest -q

# Integração do grafo
uv run pytest tests/integration/test_graph_flow.py -q

# Verificação estática
uv run ruff check .

# Build do pacote
uv build
```

A execução final no GitHub Actions após o hardening confirmou Ruff aprovado, 235 testes aprovados em 7,14 segundos, build dos pacotes concluído, risco `LOW (1/25)`, nenhuma anomalia, seis arquivos de evidência publicados e quality gate aprovado.

## 6. Limitações atuais

| Limitação | Impacto | Mitigação atual |
| --- | --- | --- |
| Relatório e índice de sessão são gravados em duas etapas | Pode ocorrer divergência entre arquivos se a segunda etapa falhar | Cada escrita é atômica; banco transacional é evolução futura |
| Persistência local não serializa múltiplos processos | Escritas concorrentes podem disputar a atualização do histórico | Escopo atual pressupõe execução sequencial |
| `thread_id` deriva de `reported_by` | Operadores diferentes possuem memórias voláteis distintas | Histórico persistente é consultado independentemente do operador |
| `MemorySaver` é volátil | Estado conversacional é perdido ao encerrar o processo | Histórico de ocorrências permanece persistido |
| Logs e auditoria são mantidos em memória | Investigação não permanece após o encerramento | Correlação é verificável durante a execução; backend durável é evolução futura |
| CLI não possui interface de aprovação humana | O exemplo `HIGH` demonstra bloqueio, não aprovação interativa | Aprovação assinada é validada deterministicamente e coberta por testes |
| Texto produzido pelo modelo permanece não determinístico | Estilo e idioma podem variar mesmo com instruções explícitas | Temperatura zero, schema, enums, sanitização e testes de comportamento |

Essas limitações representam decisões de escopo conhecidas. Elas não anulam os controles implementados nem os critérios técnicos demonstrados, mas delimitam o que seria necessário para operação concorrente e persistência de produção.
