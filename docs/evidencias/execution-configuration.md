# Configuração e Reprodução

**Data da evidência:** 2026-08-27 **Escopo:** requisitos locais, variáveis de ambiente, instalação, execução, testes e cenários reproduzíveis.

## Requisitos

- Python 3.12;
- `uv` para dependências, execução, testes e build;
- Ollama com o modelo selecionado disponível localmente;
- Flowise 3.1.3 e Node.js 22.x somente para demonstrar a automação low-code.

O Flowise é uma integração resiliente: sua ausência não impede o registro local de ocorrências autorizadas. O Ollama é necessário para uma execução real do classificador, mas é substituído por mocks nos testes automatizados.

## Instalação

Na raiz do projeto:

```bash
uv sync --locked --all-groups
```

Crie o arquivo local de configuração a partir do exemplo versionado:

```powershell
Copy-Item .env.example .env
```

O `.env` não deve ser versionado. O `.gitignore` também exclui chaves, certificados e os artefatos operacionais gerados em runtime.

## Variáveis de ambiente

| Variável | Obrigatória | Padrão no código | Finalidade |
| --- | --- | --- | --- |
| `OLLAMA_MODEL` | Não | `qwen2.5:7b` | Modelo usado pelo `ChatOllama` |
| `OLLAMA_TIMEOUT_SECONDS` | Não | `60` | Timeout de cada chamada ao modelo |
| `HUMAN_APPROVAL_SECRET` | Para aprovar `HIGH` | Sem valor | Assinar e validar aprovação HMAC |
| `FLOWISE_WEBHOOK_URL` | Não | Vazio | Endpoint `POST` do Webhook Trigger |
| `FLOWISE_TIMEOUT_SECONDS` | Não | `10` | Timeout da integração low-code |

`OLLAMA_MODEL` é lida em `src/condominium_incident_agent/llm.py`. A temperatura é fixada em zero, e falhas transitórias possuem no máximo três tentativas. Nenhuma credencial é codificada no fonte.

Exemplo local, sem valores reais:

```env
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT_SECONDS=60
HUMAN_APPROVAL_SECRET=troque-por-um-segredo-local
FLOWISE_WEBHOOK_URL=http://localhost:3000/api/v1/webhook/<AGENTFLOW_ID>
FLOWISE_TIMEOUT_SECONDS=10
```

## Preparação do modelo

```bash
ollama pull qwen2.5:7b
ollama serve
```

Se outro modelo for escolhido, altere apenas `OLLAMA_MODEL` e garanta que ele esteja disponível no Ollama. A mudança do modelo pode afetar qualidade e latência; as regras determinísticas de segurança permanecem no código.

## Execução da aplicação

Fluxo principal de acesso:

```bash
uv run python -m condominium_incident_agent.main examples/input_low.json
```

Fluxo de manutenção com severidade esperada `MEDIUM`:

```bash
uv run python -m condominium_incident_agent.main examples/input_medium.json
```

Fluxo crítico com severidade esperada `HIGH` e bloqueio sem aprovação:

```bash
uv run python -m condominium_incident_agent.main examples/input_high.json
```

A aplicação valida o JSON, cria `occurrence_id` e `correlation_id`, executa o LangGraph e apresenta a classificação e o status da integração. As respostas do LLM são não determinísticas; categoria, severidade e schema são validados antes de efeitos colaterais.

## Configuração e reprodução do Flowise

1. Instale e inicie Flowise 3.1.3.
2. Importe `flowise/workflow.json` como AgentFlow V2.
3. Salve o fluxo e abra **Embed in website or use as API**.
4. Confirme o **Webhook Trigger**, método `POST`, JSON e resposta síncrona.
5. Copie a URL exibida para `FLOWISE_WEBHOOK_URL`.
6. Execute um dos exemplos da aplicação.
7. Confira `Flowise: SENT` no terminal e localize o mesmo `correlation_id` no histórico de execução do Flowise.

O endereço de edição `/v2/agentcanvas/<id>` não é o webhook. O endpoint correto segue o formato `/api/v1/webhook/<AGENTFLOW_ID>`. Detalhes do contrato e da saída estão em `low-code.md` e no `flowise/README.md`.

## Testes, lint e build

```bash
# Suíte completa
uv run pytest -q

# Integração ponta a ponta
uv run pytest tests/integration/test_graph_flow.py -q

# Segurança adversarial
uv run pytest tests/integration/test_graph_flow.py -k prompt_injection -q

# Integração Flowise
uv run pytest tests/unit/test_flowise_webhook.py -q

# Anomalia e risco do CI
uv run pytest tests/unit/test_ci_analysis.py -q

# Qualidade estática e pacote
uv run ruff check .
uv build
```

O pipeline `.github/workflows/ci.yml` executa instalação reproduzível, Ruff, pytest com JUnit, build, análise de anomalias, relatório de risco, upload de evidências e quality gate. Os artifacts do GitHub Actions são a evidência reproduzível das execuções de CI e não dependem de arquivos locais ignorados.

## Cenários mínimos para avaliação

| Cenário | Entrada | Comportamento esperado | Evidência |
| --- | --- | --- | --- |
| Principal | `examples/input_low.json` | Classificação estruturada e, com Flowise ativo, triagem operacional | Terminal e histórico do webhook |
| Falha externa | Flowise parado | Ocorrência autorizada preservada e status `FAILED` | Teste `test_flowise_unavailable_does_not_remove_saved_occurrence` |
| Adversarial | Prompt injection em ocorrência `HIGH` | Sem aprovação, persistência ou chamada externa | Teste E2E `test_prompt_injection_cannot_approve_persist_or_call_flowise` |
| DevOps | JUnit ausente ou etapa falha | Anomalia detectada e quality gate reprovado | Testes de `ci_analysis` e artifact do CI |

## Solução de problemas

| Sintoma | Verificação |
| --- | --- |
| Ollama indisponível | Confirme `ollama serve`, modelo instalado e timeout |
| Flowise `NOT_CONFIGURED` | Preencha `FLOWISE_WEBHOOK_URL` com a URL do webhook |
| Flowise `FAILED` | Confirme serviço, ID do AgentFlow, payload e histórico do fluxo |
| `HIGH` bloqueado | Configure uma aprovação HMAC válida; texto no relato não autoriza |
| Build ou testes locais falham por ambiente | Use o GitHub Actions Linux e preserve seus logs como evidência |

## Limitações

- A aprovação humana não possui interface própria no CLI.
- Ollama e Flowise devem ser preparados fora do processo Python.
- A persistência local não foi projetada para múltiplos processos concorrentes.
- Resultados de CI só devem ser declarados após a execução correspondente no GitHub Actions.
