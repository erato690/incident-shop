# Contrato da API do incident-shop

Versão do contrato: **1.1.0** (a 1.1.0 acrescenta `GET /estatisticas_banco`; as demais rotas são as da 1.0.0). Este documento e o arquivo `docs/openapi.json` (OpenAPI, gerado
pelo FastAPI) são a fonte da verdade para as ferramentas do `incident-agent`. O OpenAPI é
verificado por teste: mudar rota, parâmetro ou campo sem atualizar o arquivo faz o teste falhar.

## Princípios

- **Só leitura**: todas as rotas são `GET`. Nenhuma rota muda estado.
- **Sem estado e determinística**: a mesma requisição devolve sempre o mesmo corpo. Não há
  relógio real; os dados vêm de uma linha do tempo fixa da loja (outubro de 2026).
- **Linha do tempo única**: os 8 cenários de incidente ocupam datas diferentes. Fora deles, a
  loja está saudável.
- **Fonte trocável**: hoje os dados são simulados (`fonte: "simulada"`). Na opção 2, serviços
  reais respondem pelas mesmas rotas e formatos (ver `docs/opcao2-servicos-reais.md`).
- **Horários**: ISO 8601 com fuso `-03:00` (horário de Brasília) nas respostas. Na entrada,
  horário sem fuso vale como `-03:00`.

## Parâmetros comuns (`/logs`, `/metricas`, `/deploys`)

(`GET /estatisticas_banco` usa só `cenario` e `servico`, descritos na própria seção.)

| Parâmetro | Tipo | Significado |
|---|---|---|
| `cenario` | texto, opcional | Id de um cenário de `GET /cenarios`. Preenche `inicio` e `fim` com a janela do cenário quando eles faltam. Id desconhecido: 404. |
| `servico` | texto, opcional | `pedidos-api`, `pagamentos-api`, `estoque-worker` ou `auth-api`. Outro valor: 422. Sem ele: todos os serviços. |
| `inicio` | data e hora, opcional | Começo da janela (inclusivo). |
| `fim` | data e hora, opcional | Fim da janela (exclusivo). |

Regras da janela:

- `/logs` e `/metricas` exigem janela: `cenario` ou o par `inicio` e `fim`. Sem isso: 422.
- `/deploys` sem janela devolve todo o histórico de deploys. Com só `inicio` ou só `fim` (sem
  `cenario`), o outro lado fica aberto: `inicio` sozinho devolve do horário em diante e `fim`
  sozinho devolve tudo antes dele; em `consulta`, o lado ausente aparece como `null`.
- `inicio` precisa ser menor que `fim`, e a janela pode ter no máximo 6 horas. Fora disso: 422.
- Com `cenario` e `inicio`/`fim` juntos, a janela explícita vale.

Erros seguem o formato padrão do FastAPI: `{"detail": "..."}` (404) ou
`{"detail": [ ... ]}` (422).

## `GET /saude`

```json
{"status": "ok", "fonte": "simulada", "versao_contrato": "1.1.0"}
```

## `GET /cenarios`

Lista os cenários e as janelas absolutas. Não expõe a causa raiz.

```json
{
  "cenarios": [
    {
      "id": "pool_esgotado",
      "titulo": "Checkout lento e erros 500 no pedidos-api",
      "servico": "pedidos-api",
      "sintoma_inicio": "2026-10-06T14:00:00-03:00",
      "janela": {"inicio": "2026-10-06T13:30:00-03:00", "fim": "2026-10-06T14:30:00-03:00"}
    }
  ]
}
```

| Cenário | Serviço | Janela padrão (-03:00) | Sintoma | Deploy na janela |
|---|---|---|---|---|
| `pool_esgotado` | pedidos-api | 2026-10-06 13:30–14:30 | 14:00 | `pedidos-api/v3.2.0` 13:40 |
| `banco_lento_com_deploy` | pedidos-api | 2026-10-08 15:15–16:15 | 15:47 | `pedidos-api/v3.2.1` 15:45 (distrator) |
| `deploy_com_bug` | pagamentos-api | 2026-10-14 14:15–15:05 | 14:38 | `pagamentos-api/v2.14.0` 14:35 |
| `env_var_faltando` | estoque-worker | 2026-10-19 16:00–16:45 | 16:21 | `estoque-worker/v1.6.0` 16:20 |
| `certificado_expirado` | auth-api | 2026-10-23 20:30–21:30 | 21:00 | nenhum |
| `vazamento_memoria` | auth-api | 2026-10-27 11:15–12:55 | 12:05 | `auth-api/v1.8.0` 11:25 |
| `gateway_fora` | pagamentos-api | 2026-10-29 08:50–10:40 | 09:10 (até 10:20) | nenhum |
| `rate_limit` | pagamentos-api | 2026-10-30 19:45–20:30 | 20:05 | nenhum |

Conversas multi-turno do agente:

- `erro_investigado` usa `pool_esgotado`. A versão real do deploy é `pedidos-api/v3.2.0`
  (reduziu `pool_max` de 20 para 10); a versão `v3.8.1` não existe no repositório.
- `escopo_externo` usa `gateway_fora` (PagaFácil fora das 09:05 às 10:20; sem deploy no dia).

## `GET /logs`

Parâmetros extras: `nivel` (`INFO`, `WARN` ou `ERROR`, filtro exato) e `limite` (1 a 5000,
padrão 500). Logs em ordem crescente de horário. `total` conta todos os logs que passam nos
filtros; `truncado` é `true` quando `total` passa de `limite`.

```bash
curl -s 'localhost:8000/logs?cenario=pool_esgotado&servico=pedidos-api&nivel=ERROR&limite=1'
```

```json
{
  "consulta": {
    "cenario": "pool_esgotado", "servico": "pedidos-api", "nivel": "ERROR",
    "inicio": "2026-10-06T13:30:00-03:00", "fim": "2026-10-06T14:30:00-03:00"
  },
  "total": 284,
  "truncado": true,
  "logs": [
    {
      "horario": "2026-10-06T14:00:07-03:00",
      "servico": "pedidos-api",
      "nivel": "ERROR",
      "mensagem": "HikariPool-1 - Connection is not available, request timed out after 3000ms (total=10, active=10, idle=0, waiting=41)\n\tat com.zaxxer.hikari.pool.HikariPool.createTimeoutException(HikariPool.java:696)\n\tat br.loja.pedidos.PedidoRepository.salvar(PedidoRepository.java:57)"
    }
  ]
}
```

## `GET /metricas`

Parâmetro extra: `metrica` (um nome da tabela abaixo; outro valor: 422). Uma série por serviço
e métrica, com um ponto por minuto da janela e um resumo.

| Métrica | Unidade | Serviços |
|---|---|---|
| `requisicoes` | req/min | todos (no `estoque-worker`: mensagens processadas por minuto) |
| `erros_5xx` | erros/min | todos |
| `latencia_p95` | ms | todos |
| `cpu` | % | todos |
| `memoria` | % | todos |
| `reinicios` | reinícios/min | todos |
| `conexoes_db` | conexões | pedidos-api, estoque-worker |
| `fila_mensagens` | mensagens | estoque-worker |

```bash
curl -s 'localhost:8000/metricas?cenario=pool_esgotado&servico=pedidos-api&metrica=conexoes_db'
```

```json
{
  "consulta": {
    "cenario": "pool_esgotado", "servico": "pedidos-api", "metrica": "conexoes_db",
    "inicio": "2026-10-06T13:30:00-03:00", "fim": "2026-10-06T14:30:00-03:00"
  },
  "series": [
    {
      "servico": "pedidos-api",
      "metrica": "conexoes_db",
      "unidade": "conexões",
      "resumo": {"min": 4.0, "max": 10.0, "media": 7.4, "ultimo": 10.0},
      "pontos": [
        {"horario": "2026-10-06T13:30:00-03:00", "valor": 4.0},
        {"horario": "2026-10-06T13:31:00-03:00", "valor": 4.0}
      ]
    }
  ]
}
```

## `GET /deploys`

Deploys reais do repositório: tag, versão e commit (7 caracteres) iguais aos do git, para o
agente comparar tags com a API do GitHub. Ordem crescente de horário.

```bash
curl -s 'localhost:8000/deploys?cenario=pool_esgotado'
```

```json
{
  "consulta": {
    "cenario": "pool_esgotado", "servico": null,
    "inicio": "2026-10-06T13:30:00-03:00", "fim": "2026-10-06T14:30:00-03:00"
  },
  "deploys": [
    {
      "horario": "2026-10-06T13:40:00-03:00",
      "servico": "pedidos-api",
      "versao": "3.2.0",
      "tag": "pedidos-api/v3.2.0",
      "commit": "a356b1f",
      "autor": "Equipe Loja",
      "mensagem": "perf: reduz pool máximo de 20 para 10 para aliviar o db-principal"
    }
  ]
}
```

Os 9 deploys (horário do deploy em produção, no mesmo horário da tag ou depois):

| Horário (-03:00) | Tag | Commit | Autor |
|---|---|---|---|
| 2026-10-01 10:00 | `pedidos-api/v3.1.0` | `7a0ac2d` | Equipe Loja |
| 2026-10-06 13:40 | `pedidos-api/v3.2.0` | `a356b1f` | Equipe Loja |
| 2026-10-08 15:45 | `pedidos-api/v3.2.1` | `60b41c3` | joao.pereira |
| 2026-10-12 10:00 | `pagamentos-api/v2.13.4` | `93bfa78` | Equipe Loja |
| 2026-10-14 14:35 | `pagamentos-api/v2.14.0` | `6245f86` | ana.souza |
| 2026-10-16 10:00 | `estoque-worker/v1.5.2` | `d63ba40` | Equipe Loja |
| 2026-10-19 16:20 | `estoque-worker/v1.6.0` | `d5c8f27` | carlos.lima |
| 2026-10-22 10:00 | `auth-api/v1.7.9` | `651362e` | Equipe Loja |
| 2026-10-27 11:25 | `auth-api/v1.8.0` | `7694861` | beatriz.alves |

## `GET /estatisticas_banco`

Retrato do banco `db-principal` no momento do início do sintoma do cenário (`sintoma_inicio`).
Parâmetros: `cenario` (obrigatório; ausente: 422; desconhecido: 404) e `servico` (opcional, os
mesmos quatro valores; outro valor: 422). Não há `inicio` nem `fim`: o retrato é de um instante, e
`consulta.momento` informa qual.

Tabelas, na ordem fixa: `pedidos` (pedidos-api), `itens_pedido` (pedidos-api), `estoque`
(pedidos-api e estoque-worker) e `reservas_estoque` (estoque-worker). Com `servico`, a lista traz
só as tabelas que ele usa; `pagamentos-api` e `auth-api` não usam o `db-principal` e recebem
`tabelas: []`.

| Campo da tabela | Significado |
|---|---|
| `tabela`, `servicos` | Nome da tabela e serviços que a usam |
| `varreduras_sequenciais` | Leituras da tabela inteira, acumuladas na última hora (inteiro) |
| `varreduras_por_indice` | Leituras pelo índice, acumuladas na última hora (inteiro) |
| `reindexacao_em_andamento` | `true` enquanto um `REINDEX` roda na tabela |
| `operacao_em_andamento` | Instrução em execução (por exemplo `REINDEX TABLE estoque`) ou `null` |
| `ultimo_analyze` | Horário do último `ANALYZE` (atualização das estatísticas do planejador) |
| `inchaco_indice_pct` | Percentual de espaço inchado nos índices, com 1 casa decimal |

Os valores são determinísticos (sementes por cenário e tabela). Estado saudável: varreduras por
índice na casa dos milhares, sequenciais na casa das dezenas, sem reindexação, `ANALYZE` às 03:00
do dia e inchaço entre 5% e 20%. Só `banco_lento_com_deploy` foge disso, na tabela `estoque`:
reindexação em andamento desde as 15:40 (coerente com os logs do `estoque-worker`), índice
indisponível durante o `REINDEX` (varreduras por índice caem para menos de 100 e as sequenciais
sobem para a casa dos milhares) e inchaço antes da reindexação entre 40% e 60%. Nos demais
cenários, inclusive `pool_esgotado` (cuja causa é o pool, não o banco), o banco aparece saudável.

```bash
curl -s 'localhost:8000/estatisticas_banco?cenario=banco_lento_com_deploy&servico=estoque-worker'
```

```json
{
  "consulta": {
    "cenario": "banco_lento_com_deploy", "servico": "estoque-worker",
    "momento": "2026-10-08T15:47:00-03:00"
  },
  "banco": "db-principal",
  "tabelas": [
    {
      "tabela": "estoque",
      "servicos": ["pedidos-api", "estoque-worker"],
      "varreduras_sequenciais": 2248,
      "varreduras_por_indice": 38,
      "reindexacao_em_andamento": true,
      "operacao_em_andamento": "REINDEX TABLE estoque",
      "ultimo_analyze": "2026-10-08T03:00:00-03:00",
      "inchaco_indice_pct": 41.0
    },
    {
      "tabela": "reservas_estoque",
      "servicos": ["estoque-worker"],
      "varreduras_sequenciais": 48,
      "varreduras_por_indice": 4686,
      "reindexacao_em_andamento": false,
      "operacao_em_andamento": null,
      "ultimo_analyze": "2026-10-08T03:00:00-03:00",
      "inchaco_indice_pct": 9.0
    }
  ]
}
```

## Gravação para o modo offline do agente

O corpo de cada resposta pode ser gravado como está. Formato sugerido para
`dados_dummy/<cenario>.json` (o script `scripts/gravar_dados_dummy.py` deste repositório já
produz esse formato, ver abaixo; a chave `estatisticas_banco` existe desde a 1.1.0):

```json
{
  "cenario": { "...": "item de GET /cenarios" },
  "logs": { "...": "corpo de GET /logs?cenario=<id>&limite=5000" },
  "metricas": { "...": "corpo de GET /metricas?cenario=<id>" },
  "deploys": { "...": "corpo de GET /deploys?cenario=<id>" },
  "estatisticas_banco": { "...": "corpo de GET /estatisticas_banco?cenario=<id>" }
}
```

Como as respostas são determinísticas, gravar duas vezes produz arquivos idênticos.

### Script `scripts/gravar_dados_dummy.py`

Grava um arquivo `<pasta>/<id>.json` por cenário de `GET /cenarios` (8 arquivos), com JSON
indentado em 2 espaços, acentos preservados, ordem dos campos mantida e newline final. Os
logs são pedidos com `limite=5000`; nenhum cenário passa disso (o maior tem 874 logs).

```bash
python scripts/gravar_dados_dummy.py dados_dummy                      # app em processo, sem rede
python scripts/gravar_dados_dummy.py dados_dummy --url http://localhost:8000   # API em execução
```

## Política de mudança

- Acréscimo compatível (campo novo, rota nova, valor novo de enumeração) sobe a versão
  secundária e é avisado ao agente. Exemplo: a 1.1.0 acrescentou a rota `GET /estatisticas_banco`
  e a chave `estatisticas_banco` no arquivo gravado, sem alterar as cinco rotas da 1.0.0.
- Remover ou renomear rota, parâmetro ou campo, ou mudar seu tipo ou significado, sobe a versão
  principal (2.0.0) e exige combinar com o agente antes.
