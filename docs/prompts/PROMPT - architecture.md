Você é um engenheiro de software sênior especializado em sistemas agênticos e LangGraph.

Revise o grafo LangGraph existente e faça apenas os ajustes necessários para atender aos requisitos de uma arquitetura agêntica clara e testável.

O grafo deve demonstrar claramente:

- `AgentState` tipado;
- nodes com responsabilidades bem definidas;
- fluxo sequencial;
- ramificação condicional;
- condição de parada;
- separação entre decisões do LLM e regras determinísticas;
- paralelização simples quando houver tarefas realmente independentes.

Se existirem tarefas independentes de recuperação de contexto, considere utilizar **fan-out/fan-in**.

Não complique o grafo sem necessidade e **não substitua a arquitetura existente sem justificativa**.

### Testes

Adicione ou atualize testes para os principais caminhos do grafo, incluindo:

- fluxo normal;
- ramificações condicionais;
- condição de parada;
- decisões determinísticas;
- caminhos paralelos, quando existentes;
- preservação dos comportamentos atuais.

### Documentação

Atualize:

```text
docs/architecture.md


Inclua:

visão geral da arquitetura;
responsabilidades dos principais nodes;
descrição dos fluxos e ramificações;
separação entre LLM e regras determinísticas;
estratégia de paralelização, quando aplicável;
diagrama Mermaid representando o grafo real implementado.
Validação

Ao final:

Execute os testes relacionados ao grafo.
Execute a suíte de testes do projeto.
Corrija problemas encontrados.
Verifique ausência de regressões.
Atualize docs/architecture.md com a implementação final.
Limites de execução

Cada comando pode ser tentado no máximo 2 vezes.

Se falhar duas vezes:

não tente novamente;
registre o problema;
prossiga quando possível;
informe ao final o comando que precisa ser executado manualmente.

O objetivo é tornar o grafo mais claro, determinístico e observável, sem adicionar complexidade desnecessária ou reescrever a arquitetura existente.
```
