# Prompts, Modelo e Ciclo de Refinamento

**Data da evidência:** 2026-08-27 **Escopo:** instruções de sistema, configuração do modelo, prompts de desenvolvimento e refinamento adversarial.

## Prompts em runtime

O principal prompt de sistema está versionado em `src/condominium_incident_agent/prompts/classifier.md`. Ele define:

- papel e objetivo do classificador;
- regras de categoria, severidade e reincidência;
- uso esperado das tools de consulta;
- proibição de inventar dados ausentes;
- limite e conteúdo do resumo;
- schema JSON obrigatório;
- tratamento do relato, histórico e resultados das tools como dados não confiáveis;
- proibição de criar aprovação ou substituir políticas de segurança.

A detecção auxiliar de incidentes múltiplos possui uma instrução de sistema curta em `nodes/validate_input.py`. Ela retorna apenas `SINGLE` ou `MULTIPLE` e usa fallback conservador em caso de falha.

## Separação entre instruções e dados

O template versionado não recebe relato, responsável ou histórico por interpolação. `prepare_context` mantém as regras em `system_instructions` e serializa os dados externos em `untrusted_input`, delimitado por `<untrusted_data>`.

`classify_incident` envia:

```text
SystemMessage(classifier.md)
HumanMessage(<untrusted_data>...</untrusted_data>)
```

A mesma fronteira é aplicada na detecção inicial. Isso torna explícito que conteúdo fornecido pelo usuário pode orientar a classificação, mas não alterar as regras do agente.

## Padrão de resposta

O LLM deve retornar somente JSON com:

```json
{
  "reasoning": {
    "base_severity": "LOW|MEDIUM|HIGH",
    "recurrence_detected": false,
    "recurrence_count": 0,
    "final_severity": "LOW|MEDIUM|HIGH"
  },
  "category": "ACCESS|PACKAGE|NOISE|MAINTENANCE|SECURITY|OTHER",
  "severity": "LOW|MEDIUM|HIGH",
  "involved_people": [],
  "apartment": null,
  "building": null,
  "summary": "Resumo objetivo em português."
}
```

O código remove fences Markdown, interpreta o JSON, valida enums e campos e interrompe o fluxo quando a resposta é inválida. O campo `reasoning` orienta o modelo, mas não é usado para autorizar efeitos críticos.

## Configuração do modelo

O modelo é configurado sem mudança de código:

```env
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT_SECONDS=60
```

`src/condominium_incident_agent/llm.py` lê as variáveis, usa temperatura zero, timeout configurável e no máximo três tentativas para falhas transitórias de rede. O modelo padrão é `qwen2.5:7b`. Credenciais e segredos não fazem parte do prompt nem da configuração versionada.

## Prompts de desenvolvimento

`docs/prompts/` registra as instruções usadas para orientar cada etapa relevante do desenvolvimento:

| Arquivo | Finalidade |
| --- | --- |
| `PROMPT - foundation.md` | Auditar e estabilizar o baseline |
| `PROMPT - test-strategy.md` | Criar a estratégia inicial de testes |
| `PROMPT - memory.md` | Refinar memória e recuperação contextual |
| `PROMPT - resilience.md` | Implementar timeout, retry e fallback |
| `PROMPT - security.md` | Implementar governança e aprovação humana |
| `PROMPT - observability.md` | Criar logs e auditoria correlacionados |
| `PROMPT - architecture.md` | Refinar responsabilidades e paralelização |
| `PROMPT - low-code.md` | Integrar o AgentFlow do Flowise |
| `PROMPT - devops-qa.md` | Criar CI, análise de logs, anomalia e risco |
| `PROMPT - security-hardening.md` | Executar validação adversarial e minimização de dados |
| `PROMPT - code-review.md` | Registrar revisão assistida por IA de alteração real |
| `PROMPT - final-documentation.md` | Consolidar critérios e evidências finais |

Esses arquivos são evidência do processo de desenvolvimento; apenas os prompts em `src/condominium_incident_agent/prompts/` e as instruções internas do código são usados em runtime.

## Ciclo de refinamento relevante

### Problema observado

Antes do hardening, `prepare_context` interpolava `user_input`, `reported_by`, data e histórico no mesmo texto enviado ao classificador. Isso enfraquecia a fronteira entre instruções confiáveis e conteúdo externo. A resposta também podia apresentar uma lista completa de visitantes autorizados, expondo dados sem necessidade.

### Hipótese e decisão

A hipótese foi que separar papéis e minimizar dados reduziria a superfície de prompt injection e vazamento sem alterar o fluxo de negócio. A decisão foi:

1. manter o template como `SystemMessage`;
2. enviar dados externos em `HumanMessage` delimitada;
3. impedir que texto ou resposta do LLM crie aprovação;
4. sanitizar entrada, resposta, persistência e resultado do Flowise;
5. mostrar apenas a confirmação relevante ao visitante mencionado.

### Alteração aplicada

O commit `0142457` (`fix: strengthen adversarial input handling`) introduziu `system_instructions` e `untrusted_input` no estado, atualizou os nodes de validação, preparação, classificação, resposta e persistência e adicionou testes unitários e de integração.

### Resultado e evidências

O cenário E2E `test_prompt_injection_cannot_approve_persist_or_call_flowise` usa uma ocorrência `SECURITY/HIGH` contendo `APPROVED` e um token. As asserções exigem:

- comando do atacante ausente das instruções de sistema;
- token redigido antes de chegar ao contexto do modelo;
- ausência de aprovação criada pelo relato ou pelo LLM;
- ausência de persistência e escalonamento;
- ausência de chamada ao Flowise;
- ausência do segredo na resposta e nos sinais de observabilidade.

Testes adicionais verificam minimização da lista de visitantes e sanitização do retorno externo. O Ruff passou após a alteração. A evidência de segurança registra que a suíte completa posterior ao hardening ainda precisa ser confirmada pelo GitHub Actions; o último CI documentado antes desse refinamento teve 226 testes, lint e build aprovados.

### Análise crítica

A mudança melhora a fronteira de confiança sem depender de um classificador de prompt injection. Ainda assim, separação de papéis e regex de sanitização não cobrem toda forma possível de ataque ou dado sensível. Em produção seriam necessários gestão de segredos, armazenamento transacional, auditoria durável e uma interface autenticada para aprovação humana.

## Reprodução

```bash
uv run pytest tests/unit/test_prepare_context.py tests/unit/test_validate_input.py tests/unit/test_classify_incident.py -q
uv run pytest tests/integration/test_graph_flow.py -k prompt_injection -q
uv run ruff check .
```

Os resultados só devem ser atualizados neste documento após execução observada.
