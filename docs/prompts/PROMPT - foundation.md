Você é um engenheiro de software sênior especializado em sistemas agênticos e LangGraph.

Trabalhe sobre o agente de classificação de ocorrências de condomínio existente no repositório. Não reconstrua a aplicação.

Inspecione o código atual e corrija problemas reais encontrados na implementação, especialmente inconsistências entre nodes, AgentState, tools, persistência, documentação e tratamento de erros.

1. Preserve as funcionalidades já existentes.
2. Corrija problemas reais encontrados na implementação atual antes de adicionar novas capacidades.
3. Analise especificamente:
   - consistência entre AgentState, nodes e persistência;
   - funcionamento de save_occurrence;
   - tratamento de exceções;
   - persistência do histórico;
   - atomicidade das operações de escrita;
   - configuração por ambiente;
   - compatibilidade entre schemas e implementação.
4. Corrija inconsistências comprovadas.
5. Não introduza tecnologias novas sem necessidade.
6. Não substitua a arquitetura atual por outra arquitetura.
7. Preserve LangGraph como mecanismo de orquestração.
8. Garanta que segredos não sejam versionados.
9. Garanta a existência de .env.example sem valores sensíveis.
10. Melhore a documentação somente onde ela estiver incompatível com o comportamento real do código.

Crie ou atualize:

`docs/evidencias/foundation.md`

Registre brevemente a arquitetura atual, problemas encontrados e correções realizadas.

Não implemente novas funcionalidades como n8n, MCP, aprovação humana ou novos serviços.

Ao final, execute o teste existente:

`uv run pytest tests/test_llm.py -vv -s`

Corrija eventuais problemas introduzidos pelas alterações.
