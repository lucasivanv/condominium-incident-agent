# Observabilidade e Rastreabilidade

**Data da evidência:** 2026-08-23 **Escopo:** execução do grafo LangGraph, logs estruturados, auditoria, decisões, latência, erros e proteção de informações sensíveis.

## Objetivo

Permitir acompanhar e investigar uma execução completa do agente sem alterar seu fluxo de negócio. Cada execução recebe um identificador único, registra as etapas relevantes em dois sinais correlacionados e expõe somente metadados necessários para diagnóstico.

## Estratégia de correlação

`IncidentInput.to_initial_state()` gera um UUID4 em `correlation_id`. O campo faz parte do `AgentState` e é preservado pelos nodes. O grafo envolve cada node com `instrument_node`, que usa o ID para registrar início, conclusão ou falha.

O ID da execução é independente do `thread_id` do `MemorySaver`: o primeiro identifica uma execução, enquanto o segundo organiza o histórico conversacional do checkpointer.

O recorder usa `threading.RLock` e filtra cada investigação pelo ID completo. Assim, registros de execuções simultâneas não são misturados no resultado.

## Sinais de observabilidade

| Sinal           | Implementação                                           | Eventos e informações                                                              |
| --------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Log operacional | Logger `agent_observation` e coleção `logs` do recorder | `started`, `completed`, `failed`, node, duração, resultado resumido e tipo de erro |
| Auditoria       | Coleção `audit` separada do logger                      | Conclusão ou falha de cada node, decisões resumidas e o mesmo `correlation_id`     |

Os dois sinais são produzidos pelo wrapper em `src/condominium_incident_agent/observability.py` e podem ser consultados independentemente.

## Formato dos registros

Os registros operacionais são emitidos como JSON com timestamp UTC:

```json
{
  "timestamp": "2026-08-23T12:00:00+00:00",
  "correlation_id": "uuid-da-execucao",
  "node": "classify_incident",
  "event": "completed",
  "duration_ms": 12.4,
  "result": {
    "category": "NOISE",
    "severity": "LOW",
    "multiple_incidents_detected": false,
    "classification_error": false,
    "escalated": false
  }
}
```

Eventos `failed` registram somente o tipo da exceção, como `RuntimeError`. Falhas controladas aparecem em `completed` com `classification_error=true`.

## Etapas e decisões registradas

| Etapa               | Decisão ou resultado observado                             |
| ------------------- | ---------------------------------------------------------- |
| `validate_input`    | Entrada validada e detecção de incidente único ou múltiplo |
| `retrieve_session_context` | Recuperação do histórico persistido relevante       |
| `retrieve_conversation_context` | Aplicação do limite conversacional             |
| `prepare_context`   | Contexto preparado para a classificação                    |
| `classify_incident` | Categoria, severidade e erro de classificação              |
| `handle_error`      | Encaminhamento de falha controlada                         |
| `save_occurrence`   | Persistência e indicação de escalonamento                  |
| `send_to_flowise`   | Status controlado da integração externa                    |
| `generate_response` | Conclusão do fluxo e estado de sucesso ou erro             |

Os resultados são resumos booleanos ou categóricos. Prompts e mensagens de conversação não fazem parte dos registros de observabilidade.

## Auditoria e investigação

Cada node concluído ou falho gera uma entrada na auditoria separada dos logs operacionais. A investigação é feita no processo atual pelo ID da execução:

```python
from condominium_incident_agent.observability import investigate_execution

execution = investigate_execution("correlation-id-da-execucao")
logs = execution["logs"]
audit = execution["audit"]
```

O retorno contém somente registros cujo `correlation_id` corresponde ao valor informado. A comparação entre `logs` e `audit` permite verificar o fluxo, as decisões, as falhas e a latência de cada etapa.

## Proteção de dados

Não são registrados:

- prompts completos e histórico de mensagens;
- relato bruto do usuário e dados desnecessários do contexto;
- tokens, senhas, chaves, credenciais ou segredos;
- conteúdo bruto de exceções;
- respostas completas do LLM.

São mantidos apenas o tipo do erro, flags de decisão, categoria, severidade, identificadores técnicos e caminhos de saída necessários para diagnóstico.

## Exemplos de execução

### Fluxo normal

1. `validate_input` registra `started` e `completed`.
2. `prepare_context` e `classify_incident` concluem com seus tempos.
3. `classify_incident` registra `category=NOISE` e `severity=LOW`.
4. `save_occurrence` registra a persistência e `send_to_flowise` registra o resultado controlado da integração.
5. `generate_response` encerra o fluxo, e logs e auditoria podem ser recuperados pelo mesmo `correlation_id`.

### Fluxo com erro

Quando a classificação não produz JSON válido, `classify_incident` registra um resultado concluído com `classification_error=true`. O fluxo segue para `handle_error` e `generate_response`, sem persistir uma ocorrência falsa.

Quando uma exceção atravessa um node, são registrados `event=failed` e o tipo da exceção, incluindo a entrada correspondente na auditoria. O conteúdo da exceção não é armazenado.

## Testes e reprodução

Os testes usam funções em memória e não dependem de serviços externos:

```bash
# Testes de observabilidade
uv run pytest tests/unit/test_observability.py

# Suíte completa e regressão do fluxo
uv run pytest

# Verificação estática dos arquivos alterados
uv run ruff check src tests
```

Os cenários cobertos incluem duração e estrutura dos logs, auditoria independente, filtragem por `correlation_id`, erros controlados e ausência de prompts, tokens e credenciais nos registros.

### Evidência de investigação ponta a ponta

O teste de integração executa o grafo completo, captura o `correlation_id` antes da chamada e consulta os dois sinais depois da execução:

```bash
uv run pytest tests/integration/test_graph_flow.py -k correlation_id -q
```

Resultado esperado:

```text
1 passed
```

A consulta confirma os nodes do caminho executado, incluindo `validate_input`, os recuperadores de contexto, `prepare_context`, `classify_incident`, `save_occurrence`, `send_to_flowise` e `generate_response`, todos com `duration_ms`, além dos registros correspondentes na auditoria. O teste também verifica que todos os registros retornados possuem exatamente o `correlation_id` da execução investigada.

## Resultado

A implementação adiciona rastreabilidade a todos os nodes registrados pelo grafo sem alterar suas regras de negócio. Na validação realizada, os testes específicos de observabilidade passaram com 4 testes e a suíte completa passou com 201 testes.

## Limitações conhecidas

- Logs e auditoria são armazenados em memória e são perdidos quando o processo termina.
- A investigação está disponível somente enquanto o processo que executou o agente permanece ativo.
- A auditoria é independente do logger operacional, mas utiliza o mesmo recorder em memória.
- O lock protege o recorder dentro do processo; persistência distribuída exigiria um backend compartilhado.
