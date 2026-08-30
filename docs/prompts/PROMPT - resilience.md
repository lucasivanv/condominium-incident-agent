Você é um engenheiro de software sênior especializado em sistemas agênticos, LangGraph, LLMs, tools e resiliência de sistemas.

O agente existente já possui uma implementação funcional. Revise e melhore o tratamento de falhas das dependências externas **sem substituir sua arquitetura atual e sem introduzir complexidade desnecessária**.

Garanta:

- tratamento adequado de falhas do LLM, incluindo Ollama quando utilizado;
- timeout em operações que possam ficar bloqueadas;
- retry limitado apenas para falhas transitórias;
- fallback quando houver alternativa segura;
- erro controlado quando não houver fallback;
- preservação do `AgentState` e do fluxo atual do LangGraph;
- ausência de respostas inventadas para mascarar falhas;
- ausência de retries ou loops infinitos.

Garanta principalmente os seguintes cenários:

- falha do LLM;
- timeout;
- falha de tool;
- falha transitória seguida de sucesso;
- limite de retries;
- fallback seguro;
- erro controlado sem fallback;
- falha de persistência, quando aplicável.

Adicione os testes necessários para demonstrar esses comportamentos.

Use mocks quando necessário para evitar dependências externas nos testes unitários.

Não introduza novas arquiteturas, serviços ou mecanismos de resiliência sem necessidade. **Preserve o fluxo atual e faça apenas as alterações necessárias para tornar o agente mais robusto e previsível.**

Crie ou atualize:

```text
docs/evidencias/resilience.md
```

Documente brevemente:

- principais dependências externas;
- estratégias de timeout e retry;
- fallbacks existentes;
- tratamento de erros sem fallback;
- como são evitados retries infinitos e respostas inventadas;
- principais cenários de falha testados.

Ao final:

1. Execute os testes relacionados à resiliência.
2. Execute a suíte de testes do projeto.
3. Corrija os problemas encontrados relacionados à implementação.
4. Verifique se não houve regressão nos comportamentos existentes.
5. Atualize `docs/evidencias/resilience.md` com o comportamento final implementado.

**### Limites de execução**

Ao executar comandos, **tente cada comando no máximo 2 vezes**.

Nunca entre em loops de tentativa.

Se um comando falhar duas vezes consecutivas:

- não tente novamente automaticamente;
- registre o problema encontrado;
- prossiga com as demais etapas quando possível;
- ao final, informe claramente qual comando precisa ser executado manualmente.

**Não altere a arquitetura existente sem justificativa. O objetivo é melhorar a resiliência atual, não reescrever o sistema.**
