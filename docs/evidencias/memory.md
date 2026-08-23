# Memory — Estratégia de Memória e Contexto

**Data da auditoria:** 2026-08-23
**Ambiente:** Windows 11, Python 3.12.13, uv, pytest 9.1.1

---

## 1. Objetivo

Usar ocorrências anteriores para identificar reincidência e fornecer contexto ao classificador, limitando o volume enviado ao LLM e mantendo a recuperação disponível após reinicializações.

## 2. Arquitetura da memória

| Componente                        | Responsabilidade                                  | Natureza               |
| --------------------------------- | ------------------------------------------------- | ---------------------- |
| `reports/session.json`            | Armazenar o histórico resumido de ocorrências     | Fonte durável          |
| `AgentState.session_history`      | Manter o snapshot do histórico durante a execução | Estado do grafo        |
| `AgentState.conversation_history` | Manter prompts, respostas do LLM e resposta final | Memória conversacional |
| `get_session_history`             | Consultar ocorrências por apartamento e bloco     | Tool do LLM            |
| `prepare_context`                 | Pré-carregar contexto relevante no prompt         | Nó do grafo            |

O `session.json` é a fonte durável. `session_history` é carregado no estado inicial e usado pelo `prepare_context`, enquanto a tool consulta novamente o arquivo persistido para refletir atualizações disponíveis durante a execução.

## 3. Fluxo do `AgentState`

1. `IncidentInput.to_initial_state()` carrega `reports/session.json` para `session_history`.
2. `prepare_context` extrai uma indicação de apartamento do relato e seleciona ocorrências correspondentes do snapshot.
3. O contexto selecionado é inserido em `{session_context}` no prompt.
4. `classify_incident` envia o prompt como mensagem mais recente ao LLM junto com as tools disponíveis.
5. O LLM pode chamar `get_session_history` para confirmar ou refinar o histórico.
6. `save_occurrence` grava a ocorrência, atualiza `session.json` e acrescenta a entrada ao `session_history`.
7. `generate_response` acrescenta a resposta final ao `conversation_history`.

Quando o contexto pré-carregado e o retorno da tool divergirem, o retorno da tool tem precedência.

### Exemplo de uso

Uma ocorrência anterior de `NOISE` é registrada para o apartamento `302`.
Em uma nova entrada como `Barulho novamente no apartamento 302`, o
`prepare_context` recupera essa ocorrência, inclui seu resumo no prompt e
orienta o LLM a confirmar o histórico com `get_session_history`. Ao identificar
reincidência da mesma categoria, o agente pode elevar a severidade conforme as
regras do classificador.

## 4. Recuperação e limites

| Limite                       | Valor | Aplicação                                               |
| ---------------------------- | ----: | ------------------------------------------------------- |
| `RECENT_CONTEXT_LIMIT`       |    10 | Ocorrências retornadas pela tool e detalhadas no prompt |
| `CONVERSATION_HISTORY_LIMIT` |     6 | Entradas preservadas antes de cada novo prompt          |

O campo `total` informa todas as ocorrências encontradas e `returned` informa quantas foram devolvidas após o limite. As ocorrências mais recentes são selecionadas pelo final da lista de inserção.

Os filtros de apartamento e bloco usam normalização segura. Registros com apartamento ou bloco nulos não interrompem a consulta e não são tratados como correspondência válida.

## 5. Persistência

Os relatórios individuais e o `session.json` são escritos em arquivos temporários no mesmo diretório e substituídos com `os.replace` após a escrita completa. Isso evita arquivos JSON parcialmente escritos após uma interrupção.

A atualização do relatório e do `session.json` ainda ocorre em duas etapas. Uma falha entre elas pode produzir uma diferença temporária entre os arquivos; o `session.json` permanece o índice usado para consultas futuras.

O fluxo pressupõe processamento sequencial. Chamadas concorrentes entre processos não são serializadas e exigiriam armazenamento transacional ou bloqueio explícito.

## 6. Testes e evidências

| Evidência                                | Cobertura                                                          |
| ---------------------------------------- | ------------------------------------------------------------------ |
| `tests/unit/test_prepare_context.py`     | Extração de apartamento, contexto granular e limite conversacional |
| `tests/unit/test_get_session_history.py` | Filtros, limites, contagens e campos nulos                         |
| `tests/unit/test_classify_incident.py`   | Envio do prompt preparado ao LLM                                   |
| `tests/unit/test_save_occurrence.py`     | Persistência, snapshot do estado e escrita atômica                 |
| `tests/unit/test_session.py`             | Leitura, recuperação de corrupção e escrita atômica da sessão      |
| `tests/integration/test_graph_flow.py`   | Pré-carregamento, persistência e uso do contexto no fluxo completo |

Os testes verificam pré-carregamento após reinicialização, inclusão do histórico no prompt, recuperação por apartamento/bloco, limites, registros opcionais nulos, atualização do snapshot e ausência de persistência após falha de classificação.

## 7. Limitações conhecidas

| Limitação                                      | Impacto                                       | Mitigação                                                  |
| ---------------------------------------------- | --------------------------------------------- | ---------------------------------------------------------- |
| Relatório e sessão não são uma transação única | Pode haver divergência temporária             | Escritas atômicas e reprocessamento                        |
| Concorrência entre processos não é serializada | Um append pode sobrescrever outro             | Processamento sequencial; storage transacional para escala |
| `MemorySaver` é volátil                        | `conversation_history` é perdido ao reiniciar | Histórico de ocorrências permanece no `session.json`       |

## 8. Validação

```bash
# Todos os testes
uv run pytest

# Testes relacionados à memória
uv run pytest tests/unit/test_session.py tests/unit/test_prepare_context.py tests/unit/test_get_session_history.py tests/integration/test_graph_flow.py
```
