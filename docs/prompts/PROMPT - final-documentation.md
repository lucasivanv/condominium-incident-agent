Você é um engenheiro de software sênior responsável por consolidar documentação técnica e evidências de um projeto acadêmico com LangGraph, Ollama, Flowise e GitHub Actions.

O projeto já possui implementação funcional e evidências separadas por tema. Consolide o material **sem inventar execuções, resultados, métricas ou artefatos externos** e sem alterar desnecessariamente a arquitetura ou o comportamento da aplicação.

### Rastreabilidade dos critérios

Crie um checklist baseado nos critérios oficiais de avaliação. Para cada critério, registre:

- status real;
- implementação correspondente;
- testes ou evidências relacionadas;
- forma de reprodução;
- pendência ou limitação, quando existir.

Diferencie claramente:

- requisito atendido pela implementação e por evidência versionada;
- requisito parcialmente atendido;
- validação dependente de serviço ou execução externa;
- atividade manual fora do repositório.

Não marque como concluído um requisito cuja evidência não possa ser localizada.

### Arquitetura e execução

Documente:

- problema, público, entradas, saídas e classificação da solução;
- LangGraph, `AgentState`, nodes, edges, ramificações e paralelização;
- separação entre decisões do LLM e regras determinísticas;
- memória, recuperação contextual e persistência;
- segurança, aprovação humana e cenário adversarial;
- logs estruturados, auditoria e `correlation_id`;
- resiliência de LLM, tools e integração externa;
- tool HTTP e workflow Flowise;
- pipeline de CI, testes, análise de anomalias e risco.

Inclua comandos de instalação, configuração, execução, testes, lint e build. Use somente variáveis presentes no `.env.example` e nunca registre valores reais de segredos.

### Prompts, modelo e refinamento

Documente:

- as principais instruções de sistema usadas em runtime;
- o contrato de resposta esperado do modelo;
- a diferença entre prompts de runtime e prompts de desenvolvimento;
- configuração do modelo por `OLLAMA_MODEL` e timeout por variável de ambiente;
- pelo menos um ciclo real de refinamento, contendo problema observado, hipótese, alteração, resultado, evidências e limitações.

O ciclo de refinamento deve apontar para código, testes, documentação e histórico reais do projeto.

### Evidências

Use os documentos de `docs/evidencias/` como fontes temáticas e faça referências relativas verificáveis. Não use diretórios ignorados pelo Git como única evidência. Para integrações externas, indique qual parte depende de execução local ou do histórico do serviço.

Corrija inconsistências materiais encontradas na documentação, principalmente quando o fluxo descrito não corresponder às edges atuais ou quando dados não confiáveis forem descritos como instruções de sistema.

### Validação

Ao final:

1. Confirme que todos os arquivos citados existem.
2. Verifique referências relativas e comandos documentados.
3. Procure links quebrados, resultados conflitantes e segredos acidentais.
4. Execute `git diff --check`.
5. Informe explicitamente as pendências manuais e as validações externas.

### Limites de execução

Ao executar comandos, **tente cada comando no máximo 2 vezes**.

Nunca entre em loops de tentativa.

Se um comando falhar duas vezes consecutivas:

- não tente novamente automaticamente;
- registre o problema encontrado;
- prossiga com as demais etapas quando possível;
- ao final, informe claramente qual comando precisa ser executado manualmente.

**Não altere o README principal nem produza roteiro de vídeo quando essas atividades estiverem explicitamente fora do escopo. O objetivo é consolidar evidências técnicas verdadeiras e reproduzíveis.**
