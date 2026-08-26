Você é um engenheiro de software sênior especializado em sistemas agênticos, LangGraph, integrações HTTP e automações low-code.

Integre o agente a uma automação low-code por meio de uma **tool HTTP**, permitindo que ocorrências autorizadas sejam encaminhadas para um workflow externo no **Flowise**.

**Não utilize MCP.**

A integração deve preservar o fluxo e as regras de segurança existentes:

LangGraph
→ classificação
→ regra determinística
→ aprovação humana quando necessária
→ HTTP Tool
→ Flowise Webhook
→ processamento
→ saída observável

### Aplicação

Implemente:

1. Uma tool HTTP para integração externa.
2. Envio da ocorrência autorizada por HTTP POST.
3. Validação determinística do payload antes do envio.
4. Inclusão do `correlation_id`.
5. Envio somente dos dados necessários.
6. Timeout e tratamento adequado de falhas.
7. Logs estruturados de sucesso e erro.
8. Testes da tool utilizando mocks para chamadas HTTP externas.

A tool não deve permitir que o LLM contorne regras de autorização ou aprovação existentes.

### Flowise

Defina a integração externa com o seguinte fluxo:

Webhook
→ processamento/validação
→ saída observável

A configuração e execução do Flowise serão realizadas externamente.

**Não declare o workflow como funcional nem simule sua execução dentro da aplicação.**

### Documentação

Crie:

```text
docs/low-code/flowise.md
```

Documente:

- endpoint e método HTTP;
- payload e campos obrigatórios;
- uso do `correlation_id`;
- validações realizadas pela aplicação;
- timeout e tratamento de erros;
- configuração esperada do Webhook no Flowise;
- processamento e validação no workflow;
- forma de saída observável;
- quais etapas dependem de configuração externa.

Não inclua credenciais, tokens ou dados sensíveis nos exemplos.

### Testes

Adicione testes para demonstrar:

- envio HTTP POST;
- validação do payload;
- inclusão do `correlation_id`;
- tratamento de timeout;
- tratamento de erro HTTP;
- registro de sucesso e falha;
- bloqueio de payload inválido;
- preservação do fluxo e das regras existentes.

### Validação

Ao final:

1. Execute os testes relacionados à integração.
2. Execute a suíte de testes do projeto.
3. Corrija os problemas encontrados relacionados à implementação.
4. Verifique se não houve regressão nos comportamentos existentes.
5. Atualize `docs/evidencias/low-code.md` com o comportamento final implementado.

### Limites de execução

Ao executar comandos, **tente cada comando no máximo 2 vezes**.

Nunca entre em loops de tentativa.

Se um comando falhar duas vezes consecutivas:

- não tente novamente automaticamente;
- registre o problema encontrado;
- prossiga com as demais etapas quando possível;
- ao final, informe claramente qual comando precisa ser executado manualmente.

**Não altere desnecessariamente a arquitetura existente. O objetivo é adicionar uma integração HTTP simples e segura com o Flowise, mantendo autorização, aprovação humana e regras determinísticas dentro da aplicação.**
