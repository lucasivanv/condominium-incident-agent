# Automação de triagem com Flowise

Este diretório contém o AgentFlow responsável pela automação low-code do
Condominium Incident Agent. Após o LangGraph classificar, autorizar e salvar uma
ocorrência, o workflow recebe os dados por webhook e produz uma triagem
operacional observável.

## Funcionalidade

```text
Webhook POST → validação → triagem operacional → auditoria → resposta HTTP
```

O Flowise:

- valida o contrato e preserva `occurrence_id` e `correlation_id`;
- define ação, prioridade, equipe responsável e SLA;
- indica se a ocorrência exige alerta;
- gera diagnóstico, timestamp e `audit_record_id`;
- devolve o resultado à aplicação, que o exibe e salva no relatório JSON.

Classificação, autorização, aprovação humana e persistência continuam sob
responsabilidade do LangGraph. Se o Flowise estiver indisponível, a ocorrência
local permanece registrada.

## Requisitos

- Node.js 22.x;
- Flowise **3.1.3**;
- aplicação principal com as dependências instaladas;
- porta 3000 disponível, salvo se outra porta for configurada.

O export não contém credenciais e não exige modelo de linguagem no Flowise.

## Instalação e configuração

1. Instale e inicie o Flowise:

   ```powershell
   npm install -g flowise@3.1.3
   npx flowise start
   ```

2. Acesse `http://localhost:3000`, crie ou abra um **AgentFlow V2** e importe
   [`workflow.json`](workflow.json).
3. Salve o AgentFlow e abra **Embed in website or use as API**.
4. Confirme que o fluxo informa **Webhook Trigger**, método `POST`, conteúdo
   `application/json` e resposta síncrona.
5. Copie a URL apresentada e configure o `.env` da aplicação:

   ```env
   FLOWISE_WEBHOOK_URL=http://localhost:3000/api/v1/webhook/<AGENTFLOW_ID>
   FLOWISE_TIMEOUT_SECONDS=10
   ```

Use sempre a URL exibida pelo Flowise, pois o identificador muda quando um novo
AgentFlow é criado ou importado.

## Uso

Com o Flowise em execução, processe uma ocorrência pela aplicação:

```powershell
uv run python -m condominium_incident_agent.main examples/input_medium.json
```

Uma execução bem-sucedida apresenta `Flowise: SENT`, ação, equipe, prioridade,
SLA e diagnóstico. O `correlation_id` exibido permite relacionar o terminal ao
histórico de execução do Flowise sem depender de artefatos locais ignorados.

Para validar a integração automatizada:

```powershell
uv run pytest tests/unit/test_flowise_webhook.py -q
```

Consulte [`docs/evidencias/low-code.md`](../docs/evidencias/low-code.md) para o
contrato completo, regras de triagem, tratamento de falhas e evidências.
