Você é um engenheiro de software sênior especializado em qualidade de software, testes automatizados e sistemas agênticos com LangGraph.

O agente existente já possui uma implementação funcional e um teste em tests/test_llm.py.

Amplie a estratégia de testes do projeto.

Crie testes unitários para os principais componentes do agente, priorizando:

- validação de entrada;
- preparação de contexto;
- classificação;
- geração de resposta;
- persistência;
- tratamento de erros.

Crie também pelo menos um teste de integração do fluxo principal do agente.

Cubra principalmente:

- ocorrência válida;
- entrada inválida;
- ocorrência crítica;
- falha de dependência;
- uso de histórico;
- persistência.

Use mocks quando necessário para evitar dependências externas nos testes unitários.

Crie:

docs/evidencias/test-strategy.md

Documente brevemente os tipos de testes e os principais cenários cobertos.

Ao final, execute os testes criados e corrija problemas encontrados.
