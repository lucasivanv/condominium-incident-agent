# Automação Low-Code com Flowise

**Data da evidência:** 2026-08-26 **Ambiente:** Windows 11, Python 3.12.13, Flowise 3.1.3, AgentFlow V2 **Escopo:** webhook HTTP, triagem operacional, integração com LangGraph, rastreabilidade, resiliência e saída observável.

## Objetivo

Demonstrar o uso efetivo de uma automação low-code durante o processamento real de ocorrências condominiais. O Flowise recebe uma ocorrência já classificada, autorizada e persistida pelo LangGraph, executa uma triagem operacional e devolve um resultado que influencia a resposta da aplicação.

A integração preserva a arquitetura existente: classificação, autorização, aprovação humana e persistência continuam sob controle determinístico da aplicação principal.

## Arquitetura da integração

O node `send_to_flowise` é executado entre `save_occurrence` e `generate_response`:

```text
LangGraph
  -> classificação e autorização
  -> persistência local
  -> HTTP POST
  -> Flowise Webhook
  -> validação e triagem
  -> registro de auditoria
  -> resposta síncrona
  -> persistência e exibição do resultado
```

O workflow importável está em `flowise/workflow.json` e utiliza nodes nativos do AgentFlow V2 compatíveis com o Flowise 3.1.3:

| Etapa | Responsabilidade |
| --- | --- |
| Webhook Trigger | Receber JSON por `POST` e iniciar o fluxo síncrono |
| Validação | Verificar campos obrigatórios, enums e `correlation_id` |
| Triagem operacional | Definir ação, prioridade, equipe, SLA e alerta |
| Auditoria | Gerar diagnóstico, timestamp e `audit_record_id` |
| Direct Reply | Retornar o resultado estruturado à aplicação |

## Contrato e rastreabilidade

A tool HTTP valida o payload com Pydantic antes de acessar a rede. O envio contém apenas os identificadores, classificação, resumo sanitizado, pessoas envolvidas e localização conhecida. Relato bruto, aprovação humana, cadastro de morador e credenciais não são encaminhados.

O `correlation_id` é obrigatório e preservado no request, processamento, resposta, logs e relatório. A aplicação rejeita respostas com correlação ou `occurrence_id` divergentes. O Flowise gera ainda:

```text
audit_record_id = flowise-<correlation_id>
```

## Processamento e saída observável

A severidade define ação, prioridade, SLA e alerta; a categoria seleciona a equipe responsável. O Flowise produz:

- `action`;
- `priority`;
- `responsible_team`;
- `sla_minutes`;
- `alert_required`;
- `diagnostic_summary`;
- `audit_record_id` e `processed_at`.

O resultado é observável em dois pontos que podem ser reproduzidos sem depender de artefatos ignorados pelo Git:

1. resposta HTTP e histórico de execução do Flowise;
2. resposta apresentada no terminal, com ação, equipe, prioridade, SLA e diagnóstico.

## Resiliência

Falhas do serviço externo não desfazem uma ocorrência já persistida. A integração utiliza timeout configurável e resultados controlados:

| Estado | Significado |
| --- | --- |
| `SENT` | Flowise respondeu e o resultado foi validado |
| `FAILED` | Timeout, conexão, erro HTTP, rejeição ou resposta inválida |
| `BLOCKED` | Payload ou configuração inválida antes do envio |
| `NOT_CONFIGURED` | `FLOWISE_WEBHOOK_URL` não foi configurada |

Logs de sucesso e falha incluem o `correlation_id`, sem registrar payload bruto, credenciais ou conteúdo integral de exceções.

## Critérios atendidos

| Critério | Evidência reproduzível |
| --- | --- |
| Trigger | Start node `webhookTrigger`, método `POST`, em `flowise/workflow.json` |
| Integração principal | Fluxo `save_occurrence -> send_to_flowise -> generate_response` |
| Processamento | Validação, triagem por categoria/severidade e auditoria visual |
| Saída observável | Resposta HTTP síncrona, histórico do Flowise e terminal |
| Rastreabilidade | `correlation_id` obrigatório e `audit_record_id` derivado |
| Resiliência | Falha externa controlada sem perda da ocorrência local |

## Evidência de execução ponta a ponta

Uma ocorrência `MAINTENANCE/LOW` foi processada com:

```text
correlation_id = 6880e3ba-f23c-462f-9ee7-7ecf3c23a924
HTTP status = 200
flowise_delivery_status = SENT
flowise_status = PROCESSED
```

A triagem retornou ação `MONITOR`, equipe `MANUTENCAO`, prioridade `NORMAL`, SLA de 1440 minutos, alerta desativado e o registro:

```text
flowise-6880e3ba-f23c-462f-9ee7-7ecf3c23a924
```

O resultado foi apresentado no terminal. O mesmo `correlation_id` permite localizar a execução correspondente no histórico do Flowise e relacioná-la aos logs estruturados da aplicação.

## Testes e reprodução

Os testes da integração cobrem POST, payload válido e inválido, correlação obrigatória e divergente, timeout, erro HTTP, indisponibilidade, rejeição do workflow, persistência do resultado e estrutura do export.

Comandos de reprodução:

```bash
# Testes específicos da integração
uv run pytest tests/unit/test_flowise_webhook.py -q

# Fluxo completo do LangGraph
uv run pytest tests/integration/test_graph_flow.py -q

# Suíte completa
uv run pytest -q

# Verificação estática
uv run ruff check src tests
```

Para a execução real, inicie o Flowise, importe `flowise/workflow.json`, configure a URL apresentada pelo Webhook Trigger e execute:

```bash
uv run python -m condominium_incident_agent.main examples/input_medium.json
```

## Resultado

A automação demonstra trigger HTTP, integração com a aplicação principal, processamento visual no Flowise, saída operacional utilizável e evidência correlacionada e reproduzível. O Flowise influencia o fluxo real sem assumir decisões críticas nem introduzir dependência obrigatória para o registro local.

## Limitações conhecidas

- Importação, publicação e disponibilidade do Flowise dependem do ambiente externo.
- O histórico de execução do Flowise não é versionado no repositório.
- A autenticação do webhook está desabilitada no ambiente acadêmico local.
- O ambiente acadêmico não utiliza um backend externo de auditoria imutável.
- Alterações no AgentFlow podem gerar um novo ID e exigir atualização de `FLOWISE_WEBHOOK_URL`.
