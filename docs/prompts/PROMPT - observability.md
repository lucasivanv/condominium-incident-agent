Você é um engenheiro de software sênior especializado em sistemas agênticos, LangGraph, observabilidade e segurança de LLMs.

Adicione observabilidade ao agente existente **sem alterar desnecessariamente sua arquitetura ou fluxo atual**.

Implemente:

- `correlation_id` único por execução, propagado por todos os nodes/etapas;
- logs estruturados contendo, quando aplicável, `correlation_id`, node, evento, duração, resultado e erros;
- registro de decisões relevantes sem armazenar prompts completos;
- proteção contra exposição de prompts, tokens, credenciais ou dados sensíveis;
- uma segunda forma de auditoria, independente dos logs operacionais, utilizando o mesmo `correlation_id`;
- uma forma simples de investigar uma execução pelo `correlation_id`.

Garanta que execuções simultâneas permaneçam corretamente isoladas.

### Testes

Adicione testes para demonstrar:

- geração e propagação do `correlation_id`;
- isolamento entre execuções;
- logs estruturados e duração das etapas;
- registro de erros e decisões relevantes;
- correlação entre logs e auditoria;
- investigação por `correlation_id`;
- ausência de prompts completos, tokens e credenciais nos registros;
- ausência de regressões no fluxo existente.

Use mocks ou implementações em memória quando necessário para evitar dependências externas.

### Documentação

Crie ou atualize:

```text
docs/evidencias/observability.md
```

Documente brevemente:

- como funciona o correlation_id;
- formato dos logs;
- mecanismo de auditoria;
- como investigar uma execução;
- informações que não são registradas por segurança;
- exemplo de execução normal;
- exemplo de execução com erro.

### Validação

Ao final:

1. Execute os testes de observabilidade.
2. Execute a suíte de testes do projeto.
3. Corrija problemas relacionados à implementação.
4. Verifique ausência de regressões.
5. Atualize a documentação com o comportamento final.

**### Limites de execução**

Ao executar comandos, **tente cada comando no máximo 2 vezes**.

Nunca entre em loops de tentativa.

Se um comando falhar duas vezes consecutivas:

- não tente novamente automaticamente;
- registre o problema encontrado;
- prossiga com as demais etapas quando possível;
- ao final, informe claramente qual comando precisa ser executado manualmente.

**Não altere a arquitetura existente sem justificativa. O objetivo é limitar a autonomia e tornar as ações críticas seguras e controláveis, não reescrever o sistema.**
