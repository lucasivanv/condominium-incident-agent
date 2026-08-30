Você é um engenheiro de software sênior especializado em sistemas agênticos, LangGraph, segurança de LLMs e controle de autonomia.

O agente existente já possui um fluxo funcional para tratamento de ocorrências. Implemente controles de segurança **sem substituir a arquitetura atual e sem introduzir complexidade desnecessária**.

O LLM deve interpretar e classificar ocorrências, mas **ações críticas devem ser controladas por regras determinísticas e nunca depender exclusivamente da decisão do LLM**.

Garanta:

- tratamento da ocorrência e demais entradas externas como dados não confiáveis;
- proteção contra prompt injection;
- validação determinística das ações antes da execução;
- proteção de credenciais, tokens e dados sensíveis;
- estado explícito de aprovação humana para ações críticas;
- bloqueio de ações críticas sem aprovação válida;
- impossibilidade de uma ocorrência ou resposta do LLM conceder aprovação por conta própria;
- preservação do `AgentState` e do fluxo atual do LangGraph.

Use uma ocorrência de **alta severidade** como cenário principal de demonstração.

Garanta principalmente os seguintes cenários:

- ocorrência contendo prompt injection;
- tentativa de executar ação crítica sem aprovação;
- ação crítica com aprovação válida;
- aprovação inválida ou expirada;
- ocorrência que tenta manipular o agente para ignorar regras de segurança;
- dados sensíveis presentes na entrada ou no contexto.

Adicione os testes necessários para demonstrar:

- resistência a prompt injection;
- bloqueio de ação crítica sem aprovação;
- execução de ação após aprovação válida;
- rejeição de aprovação inválida;
- preservação das regras de segurança independentemente da instrução fornecida pelo LLM.

Use mocks quando necessário para evitar dependências externas nos testes.

Não permita que o LLM altere diretamente regras de autorização, aprovação ou segurança. **Decisões críticas devem ser verificadas deterministicamente antes da execução.**

Crie ou atualize:

```text
docs/evidencias/security.md
```

Documente brevemente:

- quais entradas são consideradas não confiáveis;
- como o prompt injection é tratado;
- quais ações são consideradas críticas;
- como funciona a aprovação humana;
- como ações sem aprovação são bloqueadas;
- o cenário adversarial utilizado;
- o comportamento esperado e observado.

Ao final:

1. Execute os testes relacionados à segurança.
2. Execute a suíte de testes do projeto.
3. Corrija os problemas encontrados relacionados à implementação.
4. Verifique se não houve regressão nos comportamentos existentes.
5. Atualize `docs/evidencias/security.md` com o comportamento final implementado.

**### Limites de execução**

Ao executar comandos, **tente cada comando no máximo 2 vezes**.

Nunca entre em loops de tentativa.

Se um comando falhar duas vezes consecutivas:

- não tente novamente automaticamente;
- registre o problema encontrado;
- prossiga com as demais etapas quando possível;
- ao final, informe claramente qual comando precisa ser executado manualmente.

**Não altere a arquitetura existente sem justificativa. O objetivo é limitar a autonomia e tornar as ações críticas seguras e controláveis, não reescrever o sistema.**
