Você é um engenheiro de software sênior especializado em sistemas agênticos, LangGraph, segurança de LLMs, prompt injection e validação adversarial.

O projeto já possui controles de segurança, aprovação humana, persistência de ocorrências e integração com Flowise. Realize o hardening desses controles **sem substituir a arquitetura existente e sem introduzir complexidade desnecessária**.

O objetivo é garantir que entradas não confiáveis não consigam alterar instruções de sistema, conceder aprovação, executar ações críticas, persistir conteúdo indevido ou expor informações sensíveis.

### Separação de confiança

Garanta que:

- instruções permanentes sejam enviadas ao modelo como `SystemMessage`;
- ocorrências, contexto de sessão e demais dados externos sejam enviados como `HumanMessage`;
- dados externos sejam identificados explicitamente como conteúdo não confiável;
- entradas do usuário nunca sejam interpoladas nas instruções de sistema;
- respostas do LLM e de integrações externas também sejam tratadas como não confiáveis;
- o `AgentState` e o fluxo atual do LangGraph sejam preservados.

### Autorização e autonomia

Implemente ou fortaleça regras determinísticas para que:

- texto fornecido pelo usuário não possa conceder aprovação humana;
- o LLM não possa criar, alterar ou validar uma aprovação;
- ocorrências de alta severidade sejam bloqueadas sem aprovação válida;
- aprovações inválidas, ausentes ou expiradas sejam rejeitadas;
- uma aprovação válida continue permitindo o fluxo autorizado;
- uma ocorrência bloqueada não seja persistida nem encaminhada ao Flowise;
- comportamentos existentes de ocorrências de baixa e média severidade não sofram regressão.

### Proteção de dados

Minimize a exposição de dados pessoais e sensíveis:

- não exiba listas completas de visitantes, moradores ou demais cadastros;
- apresente apenas a confirmação estritamente necessária ao caso processado;
- sanitize credenciais, tokens, chaves e segredos presentes em entradas externas;
- impeça que segredos apareçam em respostas, logs, relatórios, contexto persistido ou resultados do Flowise;
- preserve informações necessárias para correlação e auditoria sem registrar conteúdo sensível.

### Validação adversarial

Use como cenário principal uma ocorrência de alta severidade contendo:

- tentativa de prompt injection;
- instrução textual para simular aprovação;
- tentativa de ignorar regras de segurança;
- pedido para persistir ou encaminhar a ocorrência;
- credencial ou token que não deve aparecer nas saídas.

Adicione ou atualize testes para demonstrar:

- separação entre `SystemMessage` e `HumanMessage`;
- ausência da entrada não confiável nas instruções de sistema;
- resistência a prompt injection;
- bloqueio de ação crítica sem aprovação válida;
- preservação de uma aprovação humana válida;
- ausência de persistência e chamada ao Flowise no cenário bloqueado;
- sanitização de respostas, logs, relatórios, memória e retorno externo;
- minimização dos dados pessoais apresentados;
- ausência de regressões no fluxo autorizado e na integração low-code.

Priorize um teste de integração ponta a ponta pelo grafo. Use mocks apenas para dependências externas e mantenha as regras de segurança reais em execução.

### Documentação

Atualize:

```text
docs/evidencias/security.md
```

Documente brevemente:

- superfícies de entrada não confiável;
- separação entre instruções e dados;
- regras determinísticas de autorização;
- minimização e sanitização de dados;
- cenário adversarial executado;
- comportamento esperado e observado;
- testes e evidências reproduzíveis;
- limitações conhecidas.

Não declare testes, execuções ou resultados que não tenham sido observados.

### Validação

Ao final:

1. Execute os testes relacionados à segurança.
2. Execute o lint do projeto.
3. Execute a suíte de testes completa.
4. Execute o build ou validação equivalente.
5. Corrija problemas relacionados à implementação.
6. Verifique se ações bloqueadas não produzem efeitos colaterais.
7. Atualize a evidência com os resultados realmente observados.

### Limites de execução

Ao executar comandos, **tente cada comando no máximo 2 vezes**.

Nunca entre em loops de tentativa.

Se um comando falhar duas vezes consecutivas:

- não tente novamente automaticamente;
- registre o problema encontrado;
- prossiga com as demais etapas quando possível;
- ao final, informe claramente qual comando precisa ser executado manualmente.

**Não altere a arquitetura existente sem justificativa. O objetivo é reforçar as fronteiras de confiança, limitar a autonomia e produzir evidências adversariais reproduzíveis, não reescrever o agente.**
