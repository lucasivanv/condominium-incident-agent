Você é um engenheiro de software sênior especializado em DevOps, QA, testes automatizados, análise de logs e gestão de risco.

O projeto já possui uma aplicação funcional com LangGraph. Implemente práticas de DevOps e QA assistidas por IA **sem alterar desnecessariamente a arquitetura ou o fluxo de negócio existente**.

O pipeline deve permanecer determinístico. A análise de anomalias e risco deve auxiliar o diagnóstico, mas nunca transformar uma falha real de lint, testes ou build em sucesso.

### Pipeline

Crie ou atualize o pipeline de CI para executar:

- instalação reproduzível das dependências;
- lint com Ruff;
- testes automatizados com relatório estruturado;
- build ou validação equivalente;
- coleta dos logs e resultados das etapas;
- publicação das evidências como artifact;
- quality gate final que falhe quando qualquer validação obrigatória falhar.

Garanta que a coleta de evidências continue quando uma etapa falhar, sem mascarar o resultado final do pipeline.

### QA assistido por IA

Utilize IA para:

- revisar uma alteração real do projeto;
- identificar problemas concretos ou oportunidades de melhoria;
- criar ou refinar testes automatizados relevantes;
- analisar criticamente as sugestões produzidas;
- registrar quais recomendações foram aceitas, rejeitadas ou ajustadas.

Priorize os testes com base em probabilidade, impacto e criticidade. Selecione e justifique explicitamente pelo menos um cenário prioritário.

### Análise de logs

Analise e explique com apoio de IA os logs de pelo menos duas etapas entre lint, testes e build.

Para cada etapa, documente:

- trecho relevante do log;
- status ou exit code;
- interpretação da IA;
- causa provável;
- impacto;
- conclusão validada com base nas evidências;
- ação recomendada, quando aplicável.

Não invente métricas, execuções ou resultados. Diferencie falhas de código, configuração, dependência e infraestrutura.

### Detecção de anomalias e risco

Implemente uma análise simples e reproduzível capaz de detectar, quando aplicável:

- falha de lint, testes ou build;
- ausência de relatório esperado;
- nenhum teste coletado;
- testes com falha ou erro;
- regressão relevante na duração da suíte.

Calcule o risco utilizando:

```text
risco = probabilidade x impacto
```

Use valores de 1 a 5 para probabilidade e impacto. Documente os níveis de risco, as regras utilizadas, a justificativa da classificação e as limitações da estimativa.

O cálculo deve ser determinístico e testável, sem depender de uma chamada a LLM durante o pipeline.

### Testes

Adicione ou atualize testes para demonstrar:

- pipeline saudável sem anomalias;
- falha de uma etapa obrigatória;
- ausência ou invalidade do relatório de testes;
- nenhum teste coletado;
- falhas registradas no relatório;
- regressão de duração em relação ao baseline;
- limites das classificações de risco;
- ausência de regressões nos comportamentos existentes.

Use mocks ou fixtures quando necessário para evitar dependências externas.

### Documentação

Crie ou atualize:

```text
docs/evidencias/devops-qa.md
docs/evidencias/test-strategy.md
```

Documente brevemente:

- arquitetura e etapas do pipeline;
- evidências produzidas;
- uso de IA em code review e testes;
- priorização dos testes por risco;
- logs analisados;
- anomalia identificada;
- método e resultado da estimativa de risco;
- comandos de reprodução;
- limitações conhecidas;
- etapas que dependem da execução externa do GitHub Actions.

### Validação

Ao final:

1. Execute os testes relacionados à análise de CI e risco.
2. Execute o lint do projeto.
3. Execute a suíte de testes completa.
4. Execute o build ou validação equivalente.
5. Corrija problemas relacionados à implementação.
6. Verifique se o quality gate não mascara falhas.
7. Atualize a documentação com os resultados realmente observados.

### Limites de execução

Ao executar comandos, **tente cada comando no máximo 2 vezes**.

Nunca entre em loops de tentativa.

Se um comando falhar duas vezes consecutivas:

- não tente novamente automaticamente;
- registre o problema encontrado;
- prossiga com as demais etapas quando possível;
- ao final, informe claramente qual comando precisa ser executado manualmente.

**Não altere a arquitetura existente sem justificativa. O objetivo é tornar as validações, anomalias e riscos observáveis e reproduzíveis, não substituir o pipeline por decisões não determinísticas de IA.**
