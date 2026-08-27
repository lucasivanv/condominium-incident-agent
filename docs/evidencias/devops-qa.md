# DevOps Inteligente e QA Assistido por IA

**Data da evidência:** 2026-08-26  
**Escopo:** CI, lint, testes, build, code review assistido por IA, detecção de
anomalias, estimativa de risco e priorização de testes.

## Objetivo

Automatizar os controles de qualidade do projeto e produzir um diagnóstico
reproduzível sem permitir que a análise de risco mascare uma falha real. O
GitHub Actions continua sendo o quality gate; a análise adiciona contexto para
investigação e priorização.

## Pipeline

O workflow `.github/workflows/ci.yml` é executado em `push` e `pull_request`
para `main` e `develop`:

```text
checkout -> dependências -> lint  ─┐
                         -> testes ├-> análise -> artifact -> quality gate
                         -> build  ─┘
```

| Etapa | Comando | Evidência produzida |
| --- | --- | --- |
| Lint | `uv run ruff check .` | `ruff.log` no artifact do CI |
| Testes | `uv run pytest --junitxml=<destino>/pytest.xml` | log e JUnit |
| Build | `uv build` | `build.log` no artifact do CI |
| Análise | `python -m condominium_incident_agent.ci_analysis` | JSON e Markdown |

Os arquivos são gerados em `runner.temp`, fora da árvore usada pelo build.
Lint, testes e build usam `continue-on-error` somente para permitir que os três
resultados sejam coletados. A última etapa verifica os outcomes e retorna erro
se qualquer validação não terminar com `success`. Portanto, uma anomalia nunca
é convertida em aprovação do pipeline.

## Uso de IA em QA

A IA foi utilizada em três atividades verificáveis:

1. revisão do diff real da estratégia de testes, documentada em
   `docs/prompts/PROMPT - code-review.md`;
2. geração e refinamento dos testes unitários e de integração, conforme
   `docs/prompts/PROMPT - test-strategy.md`;
3. revisão da Task 09, análise dos logs de lint, pytest e build e elaboração das
   regras de anomalia e risco, registrada em
   `docs/prompts/PROMPT - devops-qa.md`.

As sugestões da IA são verificadas contra código, exit codes e relatórios. O
status do pipeline, as anomalias e a pontuação não dependem de interpretação
livre de um modelo em runtime.

### Code review da Task 09

O review assistido por IA do diff identificou os seguintes riscos de desenho:

- `continue-on-error` poderia ocultar falhas se não houvesse um gate final;
- uma etapa de testes marcada como sucesso sem JUnit geraria falsa confiança;
- uma regressão de duração precisava de baseline e limite explícitos;
- artefatos gerados dentro do checkout poderiam contaminar o pacote do build;
- o analisador precisava ser testado separadamente do GitHub Actions.

As correções correspondentes foram incorporadas: `Enforce quality gate`, regra
`MISSING_JUNIT_REPORT`, limite de `1,5x` o baseline, uso de `runner.temp` e testes
unitários do analisador. O primeiro lint do novo código encontrou somente a anotação
`type[int] | type[float]`; ela foi substituída por agregadores tipados separados
e o Ruff passou na nova execução.

## Priorização de testes por risco

A prioridade considera probabilidade, impacto e criticidade da ação protegida.

| Prioridade | Cenário | Probabilidade | Impacto | Justificativa |
| --- | --- | --- | --- | --- |
| P0 | `HIGH` sem aprovação humana válida | Média | Crítico | Uma regressão permitiria persistência e escalonamento não autorizados |
| P0 | Prompt injection tentando conceder aprovação | Média | Crítico | Entrada não confiável não pode substituir a política determinística |
| P1 | Falha ou timeout do Flowise | Média | Alto | A integração externa não pode derrubar nem apagar a ocorrência local |
| P1 | Resposta inválida ou timeout do LLM | Média | Alto | O sistema não pode persistir classificação inventada ou parcial |
| P1 | Falha de persistência | Baixa | Alto | A resposta não pode afirmar sucesso sem relatório íntegro |
| P2 | Múltiplos incidentes na mesma entrada | Média | Médio | Preserva rastreabilidade, mas não executa ação irreversível |

O teste prioritário é
`test_high_severity_without_approval_is_blocked`, em
`tests/integration/test_graph_flow.py`. Ele percorre o grafo e verifica que a
ação crítica não produz relatório nem escalonamento sem uma aprovação válida.

Para a Task 09, `tests/unit/test_ci_analysis.py` cobre o detector e o cálculo de
risco, incluindo pipeline saudável, falha de testes, ausência de JUnit, zero
testes coletados, regressão de duração e limites das classificações.

## Detecção de anomalias

O módulo `src/condominium_incident_agent/ci_analysis.py` interpreta os outcomes
do GitHub Actions e o JUnit do pytest. São detectados:

- lint, testes ou build diferentes de `success`;
- teste marcado como sucesso sem relatório JUnit;
- zero testes coletados;
- falhas ou erros registrados no JUnit;
- duração maior que `1,5x` o baseline configurado.

O baseline inicial do workflow é 10 segundos. Ele é conservador em relação à
execução local e deverá ser revisto depois que houver histórico suficiente no
GitHub Actions. A igualdade com o limite não é considerada anomalia.

## Estimativa simples de risco

A fórmula é:

```text
risco = probabilidade x impacto
```

Probabilidade e impacto usam escala de 1 a 5. O risco geral é o maior valor
entre as anomalias, evitando que médias escondam uma falha crítica.

| Pontuação | Nível |
| ---: | --- |
| 1 a 4 | `LOW` |
| 5 a 9 | `MODERATE` |
| 10 a 16 | `HIGH` |
| 17 a 25 | `CRITICAL` |

Uma execução sem anomalias recebe o valor residual `1/25 (LOW)`. Falha de
testes vale `5 x 5 = 25 (CRITICAL)` e falha de build vale
`5 x 4 = 20 (CRITICAL)`.

## Análise assistida por IA dos logs

### Etapa 1 — Ruff

Log final dos arquivos da Task 09:

```text
All checks passed!
```

**Análise da IA:** não há violação estática remanescente. Na primeira execução,
o Ruff encontrou `PYI055` na união de tipos usada pelo parser JUnit. O achado
era procedente, foi corrigido e a segunda execução confirmou a resolução. Isso
demonstra um ciclo curto de detecção, correção e nova validação.

### Etapa 2 — pytest

Log dos testes criados para o analisador:

```text
...........                                                              [100%]
11 passed in 0.25s
```

O JUnit registrou 11 testes, zero falhas, zero erros e duração interna de
0,089 segundo.

**Análise da IA:** os principais limites e caminhos de falha do modelo de risco
foram exercitados. A execução isolada recebeu `1/25 (LOW)` e nenhuma anomalia.
A suíte completa não pôde ser revalidada neste host porque a coleta de módulos
que carregam dependências nativas terminou com `OPENSSL_Applink`; isso é uma
limitação do ambiente local e deverá ser confirmado pelo CI Linux.

### Etapa 3 — build

Trecho do log local:

```text
ModuleNotFoundError: No module named 'hatchling'
Failed to resolve requirements from build-system.requires
invalid peer certificate: UnknownIssuer
```

**Análise da IA:** o `pyproject.toml` declara corretamente `hatchling` em
`build-system.requires`. O build isolado tentou obter o backend e falhou por
certificado da rede; o build sem isolamento confirmou que o backend não está
instalado neste ambiente. Não há evidência de erro no pacote neste log, mas a
etapa continua operacionalmente indisponível. O detector classificou o outcome
como `BUILD_STAGE_NOT_SUCCESSFUL`, com risco `20/25 (CRITICAL)`, pois um pacote
que não pode ser construído não deve ser entregue. O GitHub Actions determinará
se a anomalia é local ou reproduzível no ambiente oficial.

## Resultados reproduzíveis

Validações concluídas nesta alteração:

```text
Ruff do projeto completo: aprovado
Testes do analisador: 11 passed
Pipeline saudável simulado com JUnit real: LOW (1/25), sem anomalia
Build local indisponível: CRITICAL (20/25), BUILD_STAGE_NOT_SUCCESSFUL
```

Comandos locais:

```powershell
uv run ruff check .
uv run pytest --junitxml=artifacts/pytest.xml
uv build
uv run python -m condominium_incident_agent.ci_analysis `
  --lint-status success `
  --test-status success `
  --build-status success `
  --junit-path artifacts/pytest.xml `
  --baseline-duration-seconds 10 `
  --json-output artifacts/ci-risk-report.json `
  --markdown-output artifacts/ci-risk-report.md
```

No GitHub Actions, o artifact `ci-quality-evidence` contém logs, JUnit e os
relatórios de risco. O resumo Markdown também é exibido na página da execução.

## Limitações

- A estimativa é heurística e serve para priorização, não como probabilidade
  estatística calibrada.
- O baseline de duração precisa ser revisto com execuções reais do CI.
- O parser utiliza os totais do JUnit e não mede cobertura de código.
- A análise de IA é evidence-based, mas exige validação dos logs e não substitui
  exit codes, testes ou revisão humana.
- A execução remota do GitHub Actions depende de `push` ou `pull_request` e não
  pode ser produzida apenas pelo repositório local.
