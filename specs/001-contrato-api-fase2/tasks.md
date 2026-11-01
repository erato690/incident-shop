# Tasks: Contrato da API da loja para a Fase 2 do agente

**Input**: `specs/001-contrato-api-fase2/` (spec, plan, research, data-model, contracts)
**Tests**: obrigatórios (constituição, princípio V): cada tarefa começa por teste que falha.

## Phase 1: Setup

- [X] T001 Criar `requirements-dev.txt` (pytest, httpx), fixar versões em `requirements.txt`,
  `tests/conftest.py` com fixture `client` e completar `.gitignore` (`.claude-flow/`, `.swarm/`,
  `ruvector.db`, `.pytest_cache/`)

## Phase 2: Foundational

- [X] T002 Modelos Pydantic de resposta em `api/modelos.py` (RegistroLog, SerieMetrica, Resumo,
  Ponto, Deploy, CenarioPublico, Janela, Consulta*, respostas das 5 rotas)
- [X] T003 [P] Interface `FonteDados` e `criar_fonte()` lendo `FONTE_DADOS` em
  `api/fontes/__init__.py`; teste em `tests/test_fonte.py` (padrão `simulada`; valor
  desconhecido gera erro claro; `servicos` gera `NotImplementedError` com mensagem da opção 2)
- [X] T004 [P] Resolução de janela em `api/janela.py` (cenario, inicio, fim, fuso -03:00, 6 horas,
  inicio < fim); teste em `tests/test_janela.py`
- [X] T005 [P] Os 9 deploys reais em `api/deploys.py`; teste em `tests/test_contrato.py` que
  compara tag, commit, autor e mensagem com o git (pula se não houver `.git`)
- [X] T006 Catálogo dos 8 cenários com datas absolutas e efeitos por minuto em `api/cenarios.py`
  (tabela da spec); semente `crc32(f"{cenario}:{minuto}")`

## Phase 3: User Story 1 - Logs, métricas e deploys por janela (P1)

- [X] T007 [US1] `FonteSimulada.logs` (estado saudável + efeitos dos cenários) em
  `api/fontes/simulada.py` e rota `GET /logs` em `api/main.py`; testes em `tests/test_logs.py`
  (sinal de cada cenário, filtros, `limite`, `truncado`, 404, 422)
- [X] T008 [US1] `FonteSimulada.metricas` e `GET /metricas`; testes em `tests/test_metricas.py`
  (um ponto por minuto, unidade, resumo, métrica anormal por cenário, 422 de métrica inválida)
- [X] T009 [US1] `GET /deploys` com filtros; testes em `tests/test_deploys.py` (deploy suspeito
  antes do sintoma; nenhum deploy nos cenários externos; histórico completo sem janela)
- [X] T010 [US1] `GET /saude` e `GET /cenarios` (sem causa raiz); testes em
  `tests/test_saude_cenarios.py`
- [X] T011 [US1] Teste de determinismo em `tests/test_determinismo.py` (mesma consulta, corpo
  idêntico; ordem de consultas não muda valores)

## Phase 4: User Story 2 - Conversas multi-turno (P1)

- [X] T012 [US2] Fatos de `erro_investigado` (cenário `pool_esgotado`) em `tests/test_conversas.py`
  e ajuste dos efeitos (deploy v3.2.0 13:40, sintoma 14:00, `waiting=41`, stack trace
  `PedidoRepository.salvar`)
- [X] T013 [US2] Fatos de `escopo_externo` (cenário `gateway_fora`) em `tests/test_conversas.py`
  e ajuste dos efeitos (502, `SocketTimeoutException`, 503, CPU normal, sem deploy no dia,
  normalização às 10:20 com pico curto de retentativas)

## Phase 5: User Story 3 - Gravação offline (P2)

- [X] T014 [US3] `scripts/gravar_dados_dummy.py <pasta> [--url URL]` (sem URL usa a app em
  processo) gravando `<cenario>.json` no formato de `docs/contrato-api.md`; teste em
  `tests/test_gravacao.py` (8 arquivos; duas gravações idênticas)

## Phase 6: User Story 4 - Contrato estável e opção 2 (P2)

- [X] T015 [US4] `scripts/exportar_openapi.py`, `docs/openapi.json` e teste em
  `tests/test_contrato.py` (OpenAPI gerado igual ao arquivo)
- [X] T016 [P] [US4] Esqueleto `api/fontes/servicos.py` e `docs/opcao2-servicos-reais.md`
  (serviços reais, coleta de logs e métricas, injeção de falha, mesma interface); teste de fonte
  falsa injetada em `tests/test_fonte.py`
- [ ] T017 [US4] Atualizar exemplos de `docs/contrato-api.md` com saídas reais da API

## Phase 7: User Story 5 - Imagem para o Railway (P3)

- [ ] T018 [US5] `Dockerfile` (dependências fixadas, usuário sem privilégio, `PORT`) e
  `railway.toml` (verificação de saúde em `/saude`); verificar `docker build` e `docker run -e
  PORT=9000` localmente. Deploy público só com confirmação do Rafael.

## Phase 8: Polish

- [ ] T019 Atualizar `README.md` (novo contrato, rotas, como rodar, sem citar aulas)
- [ ] T020 Revisão do diff (`ruflo-core:reviewer`) e `pytest -q` final

## Dependencies

- T001 antes de tudo; T002 a T006 antes das histórias (T003, T004, T005 em paralelo).
- US1 (T007 a T011) antes de US2; US3 depende de US1; T015 depende das rotas; T017 depois de
  T012 e T013; T019 e T020 no fim.
- Lote paralelo de 3 ou mais tarefas sem arquivo em comum: T003, T004, T005.
