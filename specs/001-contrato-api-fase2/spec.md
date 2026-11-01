# Feature Specification: Contrato da API da loja para a Fase 2 do agente

**Feature Branch**: `001-contrato-api-fase2`

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "Deixar a API simulada exatamente como a Fase 2 do incident-agent
precisa: logs, métricas e deploys por serviço, cenário e janela de tempo, coerentes com as tags e
os cenários do README; dados para as conversas multi-turno `erro_investigado` e `escopo_externo`;
Dockerfile e deploy no Railway (porta pela variável PORT), sem deploy público sem confirmação.
Preparar a opção 2 (serviços reais com docker compose): contrato estável (OpenAPI + documento com
exemplos), camada fonte de dados isolada (interface + implementação simulada) e esqueleto
documentado, sem implementar os serviços."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Agente consulta logs, métricas e deploys por janela (Priority: P1)

As ferramentas só leitura do agente (`buscar_logs`, `buscar_metricas`, `listar_deploys`) pedem
à API os dados de um serviço numa janela de tempo, opcionalmente nomeando o cenário (configurado
fora do modelo de linguagem). A API responde sempre a mesma coisa para a mesma pergunta, com
horários absolutos coerentes com as tags git do repositório.

**Why this priority**: sem isso a Fase 2 do agente não tem fonte de dados.

**Independent Test**: para cada um dos 8 cenários, consultar logs, métricas e deploys com
`cenario=<id>` e verificar o sinal esperado (erro característico, métrica anormal, deploy
suspeito ou ausência dele).

**Acceptance Scenarios**:

1. **Given** o cenário `deploy_com_bug`, **When** o agente pede logs do `pagamentos-api` com
   `cenario=deploy_com_bug`, **Then** recebe `NullPointerException` de `Cupom.getDesconto()` com
   horário depois do deploy `pagamentos-api/v2.14.0`.
2. **Given** o cenário `banco_lento_com_deploy`, **When** o agente lista deploys com
   `cenario=banco_lento_com_deploy`, **Then** vê `pedidos-api/v3.2.1` (commit `60b41c3`) dois
   minutos antes do sintoma, e os logs mostram a reindexação do `db-principal`.
3. **Given** um cenário de causa externa (`gateway_fora`, `certificado_expirado`, `rate_limit`),
   **When** o agente lista deploys com o cenário, **Then** nenhum deploy aparece na janela.
4. **Given** a mesma consulta repetida, **When** feita duas vezes (ou em processos diferentes),
   **Then** as respostas são idênticas byte a byte.
5. **Given** o agente sem cenário, **When** consulta com `inicio` e `fim` absolutos, **Then**
   recebe os dados da linha do tempo da loja naquela janela (incidente ou estado saudável).

---

### User Story 2 - Dados das duas conversas multi-turno do agente (Priority: P1)

As conversas `erro_investigado` e `escopo_externo` do agente precisam encontrar na API os
mesmos fatos que o engenheiro relata, com nomes e versões que existem de verdade nas tags.

**Why this priority**: as conversas são a demonstração principal da avaliação.

**Independent Test**: consultar `pool_esgotado` e `gateway_fora` e conferir cada fato citado
nas conversas.

**Acceptance Scenarios**:

1. **Given** `erro_investigado` (cenário `pool_esgotado`), **When** o agente consulta, **Then**
   vê deploy `pedidos-api/v3.2.0` em 2026-10-06 13:40 (-03:00), sintoma a partir de 14:00, log
   `HikariPool-1 - Connection is not available ... (total=10, active=10, idle=0, waiting=41)` com
   stack trace em `PedidoRepository.salvar`, erros 5xx e latência alta no `pedidos-api`.
2. **Given** `escopo_externo` (cenário `gateway_fora`), **When** o agente consulta, **Then** vê
   em 2026-10-29 a partir de 09:10 o `pagamentos-api` devolvendo 502, `SocketTimeoutException`
   e HTTP 503 ao chamar `api.pagafacil.com.br`, uso de processador normal, nenhum deploy no dia,
   e normalização a partir de 10:20 com um pico curto de retentativas.

---

### User Story 3 - Gravar dados para o modo offline do agente (Priority: P2)

O agente grava `dados_dummy/<cenario>.json` a partir da própria API para rodar sem rede.

**Why this priority**: o notebook do agente precisa rodar sem a loja no ar.

**Independent Test**: `GET /cenarios` lista os 8 cenários com janela; um script do agente
grava os JSON e uma segunda gravação produz arquivos idênticos.

**Acceptance Scenarios**:

1. **Given** a API, **When** se pede `GET /cenarios`, **Then** vêm os 8 cenários com `id`,
   `titulo`, `servico`, `janela.inicio`, `janela.fim` e `sintoma_inicio`, sem a causa raiz.
2. **Given** um cenário, **When** se grava logs, métricas e deploys, **Then** o JSON gravado é
   igual ao corpo das respostas da API (mesmo formato), para o agente ler sem adaptação.

---

### User Story 4 - Contrato estável e caminho para serviços reais (Priority: P2)

Quem constrói o agente lê `docs/contrato-api.md` e o OpenAPI e sabe exatamente o que chamar. No
futuro, a fonte simulada é trocada por serviços reais sem mudar o contrato.

**Why this priority**: o agente é construído em paralelo; a opção 2 vem depois da entrega.

**Independent Test**: teste de contrato compara o OpenAPI gerado com `docs/openapi.json`; uma
fonte falsa injetada responde pelas mesmas rotas.

**Acceptance Scenarios**:

1. **Given** o código, **When** o OpenAPI gerado difere de `docs/openapi.json`, **Then** o
   teste de contrato falha.
2. **Given** outra implementação da interface fonte de dados, **When** injetada, **Then** as
   rotas respondem com ela sem mudar código das rotas.
3. **Given** `docs/opcao2-servicos-reais.md`, **When** lido, **Then** explica como os quatro
   serviços reais, a coleta de logs e métricas e a injeção de falha se encaixam na interface.

---

### User Story 5 - Imagem para o Railway (Priority: P3)

A API roda numa imagem Docker que lê a porta de `PORT`, pronta para o Railway.

**Independent Test**: `docker build` e `docker run -e PORT=9000`; `GET /saude` responde na
porta 9000. O deploy público só acontece com confirmação do Rafael.

---

### Edge Cases

- Cenário inexistente: 404 com mensagem legível.
- Sem `cenario` e sem `inicio` ou `fim`: 422 explicando que é preciso um dos dois.
- `inicio` maior ou igual a `fim`, ou janela maior que 6 horas: 422.
- Horário sem fuso: interpretado como -03:00 (horário de Brasília).
- Serviço desconhecido: 422 listando os quatro serviços válidos.
- Janela fora de qualquer incidente: dados saudáveis (poucos logs INFO, métricas normais).
- Muitos logs: corte em `limite` (padrão 500, máximo 5000) com `total` e `truncado`.
- `cenario` com `inicio`/`fim`: a janela explícita vale; o cenário só preenche o que faltar.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A API MUST expor só rotas de leitura: `GET /saude`, `GET /cenarios`,
  `GET /logs`, `GET /metricas`, `GET /deploys`. A rota com estado `POST /cenarios/{id}` sai do
  contrato 1.0 (decisão do conductor) e a injeção de falha fica documentada para a opção 2.
- **FR-002**: Os 8 cenários MUST ocupar datas absolutas distintas numa linha do tempo única da
  loja, coerentes com as datas das tags (tabela em Key Entities).
- **FR-003**: `GET /logs`, `GET /metricas` e `GET /deploys` MUST aceitar `servico`, `inicio`,
  `fim` e `cenario` opcionais, com o mesmo significado nas três rotas; `cenario` preenche a
  janela padrão do cenário.
- **FR-004**: `GET /logs` MUST aceitar `nivel` (`INFO`, `WARN`, `ERROR`, filtro exato) e
  `limite`; MUST devolver logs em ordem de horário, com `total` e `truncado`.
- **FR-005**: `GET /metricas` MUST aceitar `metrica` e devolver séries por serviço e métrica,
  um ponto por minuto, com unidade e resumo (mínimo, máximo, média, último).
- **FR-006**: `GET /deploys` MUST devolver os 9 deploys reais (4 de base e 5 de mudança) com
  tag, versão, commit curto e autor iguais aos do git; filtros por serviço e janela.
- **FR-007**: As respostas MUST ser determinísticas (sem relógio real, aleatoriedade com semente
  por cenário e minuto).
- **FR-008**: `GET /cenarios` MUST listar id, título, serviço afetado, janela e início do
  sintoma; MUST NOT expor a causa raiz.
- **FR-009**: As rotas MUST depender só de uma interface fonte de dados; a implementação
  simulada é a padrão; a escolha vem da variável `FONTE_DADOS` (`simulada`; `servicos`
  reservada para a opção 2, com erro claro enquanto não existir).
- **FR-010**: `docs/openapi.json` MUST ser gerado do FastAPI por script versionado e verificado
  por teste; `docs/contrato-api.md` MUST trazer cada rota com exemplo de requisição e resposta.
- **FR-011**: `GET /saude` MUST devolver `status`, `fonte` e `versao_contrato` (`1.0.0`).
- **FR-012**: A imagem Docker MUST escutar na porta de `PORT` (padrão 8000).
- **FR-013**: `docs/opcao2-servicos-reais.md` MUST descrever o encaixe da opção 2 sem
  implementá-la, e a implementação `servicos` MUST existir só como esqueleto.
- **FR-014**: O README MUST ser atualizado para o novo contrato, sem citar aulas.

### Key Entities

- **Cenário**: id, título, serviço afetado, janela (início e fim, -03:00), início do sintoma.

  | Cenário | Serviço | Deploy na janela | Sintoma | Janela padrão |
  |---|---|---|---|---|
  | `pool_esgotado` | pedidos-api | v3.2.0 em 2026-10-06 13:40 | 14:00, 30 min | 13:30–14:30 |
  | `banco_lento_com_deploy` | pedidos-api | v3.2.1 em 2026-10-08 15:45 (distrator) | 15:47, 25 min | 15:15–16:15 |
  | `deploy_com_bug` | pagamentos-api | v2.14.0 em 2026-10-14 14:35 | 14:38, 25 min | 14:15–15:05 |
  | `env_var_faltando` | estoque-worker | v1.6.0 em 2026-10-19 16:20 | 16:21, 20 min | 16:00–16:45 |
  | `certificado_expirado` | auth-api | nenhum | 2026-10-23 21:00, 30 min | 20:30–21:30 |
  | `vazamento_memoria` | auth-api | v1.8.0 em 2026-10-27 11:25 | 12:05, 48 min | 11:15–12:55 |
  | `gateway_fora` | pagamentos-api | nenhum | 2026-10-29 09:10 até 10:20 | 08:50–10:40 |
  | `rate_limit` | pagamentos-api | nenhum | 2026-10-30 20:05, 20 min | 19:45–20:30 |

- **Log**: horário, serviço, nível, mensagem.
- **Série de métrica**: serviço, métrica, unidade, pontos (horário, valor), resumo.
- **Deploy**: serviço, versão, tag, commit, autor, mensagem, horário.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Os 8 cenários e as 2 conversas são reproduzíveis por consulta: 100% dos fatos
  citados nas conversas aparecem na API.
- **SC-002**: Duas gravações seguidas dos 8 cenários produzem arquivos idênticos.
- **SC-003**: 100% das versões e commits listados em `/deploys` existem nas tags do git.
- **SC-004**: `pytest -q` passa sem rede; o teste de contrato acusa qualquer mudança de rota.
- **SC-005**: A imagem sobe e responde `/saude` em menos de 10 segundos numa porta escolhida.

## Assumptions

- A conversa `erro_investigado` do agente cita uma versão `v3.8.1` que não existe; a tag real
  é `pedidos-api/v3.2.0` (pool de 20 para 10). A sessão do agente troca o texto da conversa;
  este repositório não cria tag nova.
- O deploy em produção acontece minutos depois da criação da tag (ex.: tag `v3.2.0` às 09:50,
  deploy às 13:40).
- O fuso de todos os horários é -03:00.

## Clarifications

### Session 2026-11-01

Decisões tomadas pelo Jev (TypeSafe, `jev-1.14.0`) e pelo conductor:

- Q: Como alinhar a conversa `erro_investigado` (v3.8.1) com as tags? → A: usar a tag real
  `pedidos-api/v3.2.0`, deploy 13:40, sintoma 14:00; a sessão do agente ajusta o texto
  (Jev, confiança 0.98).
- Q: Modelo de consulta? → A: linha do tempo única sem estado, datas absolutas, filtros
  `servico`, `inicio`, `fim` e `cenario` opcional (Jev, confiança 0.94).
- Q: Rota com estado `POST /cenarios/{id}`? → A: remover do contrato 1.0 e documentar a injeção
  futura no esqueleto da opção 2 (Jev 0.66, abaixo de 0.7; decidido pelo conductor: opção A).
- Pedido do conductor: `cenario` filtra igual nas três rotas; `GET /cenarios` somente leitura
  com janela absoluta; dados gravados em JSON no mesmo formato das respostas.
