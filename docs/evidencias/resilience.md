# Resiliência das dependências

**Data da evidência:** 2026-08-23 **Escopo:** Ollama, chamadas de tools, memória persistente e fluxo LangGraph.

## Objetivo e princípio de segurança

O agente deve continuar de forma segura quando uma dependência externa falhar, mas não pode transformar uma falha em uma classificação inventada. Por isso, há três resultados possíveis:

1. recuperar uma falha transitória dentro de limites explícitos;
2. usar um fallback conservador quando a decisão puder ser tomada sem inventar dados;
3. interromper a etapa dependente e encaminhar um erro controlado ao usuário.

O fluxo de erro preserva o grafo existente:

```text
classify_incident -> handle_error -> generate_response -> END
```

Uma falha de classificação não alcança `save_occurrence`, portanto não gera um relatório que pareça ter sido registrado com sucesso.

## Políticas por dependência

| Dependência ou etapa | Controle | Limite e comportamento após falha |
| --- | --- | --- |
| Ollama | Timeout configurável por `OLLAMA_TIMEOUT_SECONDS` | 60 segundos por padrão; a chamada termina com erro após o timeout |
| Ollama | Retry seletivo | No máximo 3 tentativas, somente para `TimeoutError`, `ConnectionError` e erros transitórios de timeout/rede do `httpx` |
| Classificação com tools | Loop agentic limitado | No máximo 5 iterações; se não houver resposta final, retorna `classification_error` |
| `lookup_resident` e `get_session_history` | Erro controlado, sem retry automático | A falha não é usada para preencher dados ausentes; a classificação é interrompida |
| Detecção de múltiplos incidentes | Fallback conservador | Se o LLM falhar nessa etapa auxiliar, assume-se um único incidente e o fluxo tenta a classificação normal |
| Relatório e `session.json` | Escrita atômica com arquivo temporário e `os.replace` | Falha de filesystem retorna erro controlado; a resposta não afirma que a ocorrência foi salva |

Falhas definitivas, como erro de validação, não são repetidas. Tools locais também não são repetidas automaticamente, pois podem futuramente possuir efeitos colaterais. Isso evita duplicação de ações e mantém o comportamento previsível.

## Relação com memória e persistência

O `session.json` é a fonte durável das ocorrências. O `AgentState.session_history` é um snapshot usado pelo `prepare_context`, enquanto `get_session_history` consulta o arquivo persistido. Os limites de contexto reduzem o impacto de arquivos grandes:

- `RECENT_CONTEXT_LIMIT = 10` ocorrências por consulta;
- `CONVERSATION_HISTORY_LIMIT = 6` entradas no histórico conversacional;
- `MemorySaver` preserva o estado entre invocações do mesmo processo, mas é volátil após reinicialização.

Relatório e sessão são gravados em etapas distintas, portanto não formam uma transação única. Uma falha entre as etapas pode causar divergência temporária; as escritas atômicas evitam JSON parcialmente gravado, mas não substituem um storage transacional. O projeto também pressupõe processamento sequencial; execuções concorrentes exigiriam bloqueio ou armazenamento apropriado.

## Testes e evidências

Os testes unitários usam mocks para simular dependências externas de forma determinística, sem exigir Ollama ativo. Os testes de integração executam o grafo completo com LLM e filesystem isolados, verificando que o roteamento e a persistência permanecem corretos.

Os cenários de resiliência cobertos incluem:

- falha de conexão do LLM sem classificação parcial;
- timeout do LLM convertido em erro controlado;
- falha de tool sem resposta de sucesso falsa;
- falha de persistência sem `output_file` ou `escalated_file` válido;
- recuperação após uma falha transitória na segunda tentativa;
- encerramento exatamente no limite de 3 tentativas;
- ausência de retry para erro não transitório;
- limite de 5 iterações do loop de tools;
- fallback da detecção de múltiplos incidentes para incidente único.

Comandos de reprodução:

```bash
# Testes de resiliência do LLM e da classificação
uv run pytest tests/unit/test_classify_incident.py

# Persistência e tratamento de falhas de filesystem
uv run pytest tests/unit/test_save_occurrence.py tests/unit/test_session.py

# Fluxo completo do LangGraph
uv run pytest tests/integration/test_graph_flow.py

# Suíte completa
uv run pytest
```

## Resultado

A política impede retry infinito, não mascara indisponibilidade de dependência com dados inventados e mantém as condições de parada do agente. Na validação mais recente, a suíte completa passou com 189 testes e o Ruff não encontrou erros nos arquivos alterados.

## Limitações conhecidas

- Os testes de indisponibilidade usam mocks; eles não substituem uma demonstração operacional com Ollama real.
- Não há failover para outro modelo ou provedor: quando a classificação falha, o usuário recebe erro controlado.
- A sessão não possui transação única entre relatório e índice persistente.
- O fallback de detecção de múltiplos incidentes é deliberadamente limitado: ele não classifica, resume nem salva a ocorrência por conta própria.
