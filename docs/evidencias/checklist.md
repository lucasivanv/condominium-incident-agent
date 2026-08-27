# Checklist dos Critérios de Avaliação

**Data da consolidação:** 2026-08-27 **Fonte:** Projeto Avaliativo M2S08, critérios 1 a 15. **Escopo desta entrega:** documentação técnica, evidências e README principal; vídeo não incluído.

## Legenda

- **Atendido:** implementação e evidência versionada localizadas.
- **Atendido; validar execução final:** implementação e testes existem, mas a execução posterior à alteração ainda deve ser registrada pelo CI.
- **Pendente:** não concluído dentro do escopo atual.
- **Manual externo:** depende de GitHub, YouTube ou outra interface externa.

## Matriz de rastreabilidade

| Nº | Critério resumido | Status | Implementação e evidência | Reprodução ou verificação |
| ---: | --- | --- | --- | --- |
| 1 | Vídeo de demonstração | **Pendente — fora do escopo** | Não produzido nesta task por solicitação explícita | Atividade manual futura |
| 2 | Escopo organizado em cards | **Atendido** | GitHub Project organizado com cards relacionados às atividades do projeto, conforme confirmação do responsável | Conferir descrições e vínculos dos cards no GitHub Project |
| 3 | Movimentação real dos cards | **Atendido** | Evolução dos cards registrada no quadro durante o desenvolvimento, conforme confirmação do responsável | Conferir histórico e situação final dos cards no GitHub Project |
| 4 | Branches, commits e fluxo de versionamento | **Atendido** | Histórico contém feature branches, PRs, merges e commits semânticos; exemplos: `f201496`, `0d1ce34` e `0142457` | `git log --graph --oneline --decorate --all` e aba de Pull Requests |
| 5 | README e documentação permitem compreender e executar | **Atendido** | O `README.md` apresenta evolução do fork, domínio, arquitetura, configuração, execução, cenários, segurança, memória, Flowise, QA, CI e evidências | Seguir a instalação e executar os cenários e comandos documentados no README |
| 6 | Aplicação funcional e dois cenários | **Atendido** | [Arquitetura](architecture.md), [configuração](execution-configuration.md), exemplos e teste E2E demonstram fluxo principal e cenário adversarial | Executar os dois cenários descritos em `execution-configuration.md` |
| 7 | LangGraph com state, nodes, edges, ramificação e paralelização | **Atendido** | [Arquitetura](architecture.md), `graph.py`, `state.py` e `test_graph_flow.py` | `uv run pytest tests/integration/test_graph_flow.py -q` |
| 8 | Tool integrada com validação e falhas | **Atendido** | `flowise_webhook.py`, [evidência low-code](low-code.md) e `test_flowise_webhook.py` cobrem POST, Pydantic, correlação, timeout e erros | `uv run pytest tests/unit/test_flowise_webhook.py -q` |
| 9 | Memória ou recuperação contextual | **Atendido** | [Memória](memory.md), `MemorySaver`, sessão persistente, fan-out de contexto e tool de histórico | Executar os testes indicados em `memory.md` |
| 10 | Segurança e limites de autonomia | **Atendido; validar execução final** | [Segurança](security.md), [refinamento](prompts-model-refinement.md), aprovação HMAC e teste adversarial E2E | `uv run pytest tests/integration/test_graph_flow.py -k prompt_injection -q` e GitHub Actions |
| 11 | Dois sinais correlacionados e resiliência | **Atendido** | [Observabilidade](observability.md) registra logs e auditoria por `correlation_id`; [resiliência](resilience.md) cobre timeout, retry, fallback e escrita atômica | Executar testes de observabilidade e resiliência citados nos documentos |
| 12 | IA em code review e testes priorizados | **Atendido** | [DevOps e QA](devops-qa.md), [estratégia de testes](test-strategy.md) e `PROMPT - code-review.md` registram revisão real, decisões e prioridade P0 | Revisar prompts, testes E2E e matriz de risco |
| 13 | CI, logs, anomalia e risco | **Atendido** | `.github/workflows/ci.yml`, `ci_analysis.py`, testes do analisador e [evidência DevOps](devops-qa.md) | `uv run pytest tests/unit/test_ci_analysis.py -q` e conferir artifact `ci-quality-evidence` |
| 14 | Automação low-code integrada | **Atendido** | `flowise/workflow.json`, tool HTTP, node `send_to_flowise`, [guia do Flowise](../../flowise/README.md) e [evidência](low-code.md) | Importar o AgentFlow, configurar webhook e executar `input_medium.json` |
| 15 | Refinamento relevante e evidenciado | **Atendido** | [Prompts, modelo e refinamento](prompts-model-refinement.md) documenta problema, hipótese, alteração `0142457`, teste adversarial e limitações | `git show 0142457` e comandos de reprodução do documento |

## Relação entre requisitos técnicos e evidências

| Área | Implementação principal | Testes principais | Evidência narrativa |
| --- | --- | --- | --- |
| Domínio e baseline | `main.py`, `schemas.py`, exemplos | `test_schemas.py`, `test_graph_flow.py` | [Foundation](foundation.md) |
| Arquitetura | `graph.py`, `state.py`, nodes | `test_graph_flow.py` | [Arquitetura](architecture.md) |
| Memória | `session.py`, `prepare_context.py`, `get_session_history.py` | `test_session.py`, `test_prepare_context.py`, `test_get_session_history.py` | [Memória](memory.md) |
| Segurança | `security.py`, `save_occurrence.py`, prompts | `test_security.py`, teste E2E adversarial | [Segurança](security.md) |
| Observabilidade | `observability.py`, wrappers do grafo | `test_observability.py`, teste correlacionado E2E | [Observabilidade](observability.md) |
| Resiliência | `llm.py`, tratamento de tools e persistência | testes de classificação, sessão e persistência | [Resiliência](resilience.md) |
| Low-code | `flowise_webhook.py`, `send_to_flowise.py`, workflow exportado | `test_flowise_webhook.py`, fluxo integrado | [Low-code](low-code.md) |
| QA e testes | suíte unitária e de integração | `tests/` | [Estratégia de testes](test-strategy.md) |
| DevOps inteligente | workflow CI e `ci_analysis.py` | `test_ci_analysis.py` | [DevOps e QA](devops-qa.md) |
| Prompts e modelo | `classifier.md`, `llm.py`, `.env.example` | testes de preparação e classificação | [Prompts e refinamento](prompts-model-refinement.md) |
| Configuração | `pyproject.toml`, `uv.lock`, `.env.example` | CI executa instalação, testes e build | [Configuração e reprodução](execution-configuration.md) |

## Checklist da consolidação documental

- [x] Criar checklist dos critérios de avaliação.
- [x] Relacionar critérios à implementação e às evidências.
- [x] Documentar arquitetura, execução e dois cenários.
- [x] Documentar configuração e reprodução.
- [x] Relacionar memória, segurança, observabilidade e resiliência.
- [x] Relacionar tool HTTP e Flowise.
- [x] Relacionar testes, CI, análise de logs, anomalia e risco.
- [x] Documentar prompts e instruções de sistema.
- [x] Documentar configuração do modelo por variável de ambiente.
- [x] Documentar um ciclo real de refinamento.
- [x] Criar o prompt desta task no padrão do projeto.
- [x] Revisar e atualizar o `README.md` principal.
- [ ] Criar roteiro e gravar vídeo — fora do escopo solicitado.

## Pendências antes da entrega final

1. Executar o GitHub Actions após esta consolidação e após o hardening; registrar o total e o status realmente observados, sem substituir resultados históricos.
2. Produzir o vídeo apenas na etapa manual posterior.

## Conclusão

Os critérios 2 a 15 possuem implementação ou evidência rastreável e foram registrados como atendidos. O vídeo do critério 1 continua pendente por estar fora do escopo desta etapa. A suíte posterior ao hardening deve ser confirmada pelo pipeline antes de a entrega ser declarada integralmente validada.
