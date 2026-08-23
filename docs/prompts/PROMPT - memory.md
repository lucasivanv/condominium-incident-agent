Você é um engenheiro de software sênior especializado em sistemas agênticos, LangGraph, gerenciamento de estado, memória e persistência confiável.

O agente existente já possui uma implementação funcional de memória/histórico de ocorrências. Revise e melhore a estratégia de memória existente **sem substituir sua arquitetura atual e sem introduzir complexidade desnecessária**.

Amplie a implementação para garantir que a memória seja corretamente recuperada, limitada, utilizada pelo agente e persistida sem perda de dados.

Priorize:

- uso correto do `AgentState`;
- recuperação de ocorrências anteriores relevantes ao contexto atual;
- seleção de histórico relevante, evitando inserir todo o histórico no prompt;
- limite explícito para a quantidade de contexto recuperado;
- utilização efetiva do contexto recuperado pelo agente;
- preservação dos dados existentes em escritas consecutivas;
- comportamento previsível quando não houver histórico;
- isolamento adequado da memória durante os testes.

Garanta principalmente os seguintes cenários:

- ocorrência sem histórico anterior;
- ocorrência relacionada a ocorrências anteriores;
- existência de histórico irrelevante;
- limite de quantidade de ocorrências recuperadas;
- utilização do histórico recuperado na preparação do contexto/prompt;
- múltiplas escritas consecutivas sem perda de dados;
- persistência e recuperação correta dos dados;
- falha ou ausência de dados persistidos.

Adicione os testes necessários para demonstrar:

- recuperação de ocorrências anteriores;
- filtragem de contexto relevante;
- aplicação do limite de histórico;
- utilização do histórico pelo agente;
- persistência correta entre escritas consecutivas;
- comportamento quando não existe histórico.

Use mocks quando necessário para evitar dependências externas nos testes unitários.

Não introduza RAG, banco de dados externo, embeddings ou outra arquitetura de recuperação sem necessidade. **Preserve a arquitetura atual e faça apenas as alterações necessárias para tornar a estratégia de memória mais robusta e testável.**

Crie ou atualize:

```text
docs/evidencias/memory.md
```

Documente brevemente:

- como a memória funciona atualmente;
- onde o histórico é armazenado;
- como ocorrências anteriores são recuperadas;
- como o histórico é limitado/filtrado;
- como o contexto recuperado chega ao agente;
- como a persistência evita perda de dados;
- um exemplo simples de uso de contexto de uma ocorrência anterior.

Ao final:

1. Execute os testes relacionados à memória.
2. Execute a suíte de testes do projeto.
3. Corrija os problemas encontrados que sejam relacionados à implementação realizada.
4. Verifique se não houve regressão nos comportamentos existentes.
5. Atualize `docs/evidencias/memory.md` com o comportamento final implementado.

### Limites de execução

Ao executar comandos, **tente cada comando no máximo 2 vezes**.

Nunca entre em loops de tentativa.

Se um comando falhar duas vezes consecutivas:

- não tente novamente automaticamente;
- registre o problema encontrado;
- prossiga com as demais etapas quando possível;
- ao final, informe claramente qual comando precisa ser executado manualmente.

**Não altere a arquitetura existente sem justificativa. O objetivo é melhorar a estratégia de memória atual, não reescrever o sistema.**
