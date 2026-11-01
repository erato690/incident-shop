# Contrato da API do incident-shop

Versão do contrato: **1.0.0**. Este documento e o arquivo `docs/openapi.json` (OpenAPI, gerado
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

| Parâmetro | Tipo | Significado |
|---|---|---|
| `cenario` | texto, opcional | Id de um cenário de `GET /cenarios`. Preenche `inicio` e `fim` com a janela do cenário quando eles faltam. Id desconhecido: 404. |
| `servico` | texto, opcional | `pedidos-api`, `pagamentos-api`, `estoque-worker` ou `auth-api`. Outro valor: 422. Sem ele: todos os serviços. |
| `inicio` | data e hora, opcional | Começo da janela (inclusivo). |
| `fim` | data e hora, opcional | Fim da janela (exclusivo). |

Regras da janela:

- `/logs` e `/metricas` exigem janela: `cenario` ou o par `inicio` e `fim`. Sem isso: 422.
- `/deploys` sem janela devolve todo o histórico de deploys.
- `inicio` precisa ser menor que `fim`, e a janela pode ter no máximo 6 horas. Fora disso: 422.
- Com `cenario` e `inicio`/`fim` juntos, a janela explícita vale.

Erros seguem o formato padrão do FastAPI: `{"detail": "..."}` (404) ou
`{"detail": [ ... ]}` (422).

## `GET /saude`

```json
{"status": "ok", "fonte": "simulada", "versao_contrato": "1.0.0"}
```

## `GET /cenarios`

Lista os cenários e as janelas absolutas. Não expõe a causa raiz.

```json
{
  "cenarios": [
    {
      "id": "pool_esgotado",
      "titulo": "Pool de conexões esgotado no pico",
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
  "total": 287,
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
        {"horario": "2026-10-06T13:30:00-03:00", "valor": 5.0},
        {"horario": "2026-10-06T13:31:00-03:00", "valor": 6.0}
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
      "mensagem": "perf: reduz pool máximo de 20 para 10 para aliviar o banco"
    }
  ]
}
```

Os 9 deploys (horário do deploy em produção, depois da criação da tag):

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

## Gravação para o modo offline do agente

O corpo de cada resposta pode ser gravado como está. Formato sugerido para
`dados_dummy/<cenario>.json` (montado pelo script do agente):

```json
{
  "cenario": { "...": "item de GET /cenarios" },
  "logs": { "...": "corpo de GET /logs?cenario=<id>&limite=5000" },
  "metricas": { "...": "corpo de GET /metricas?cenario=<id>" },
  "deploys": { "...": "corpo de GET /deploys?cenario=<id>" }
}
```

Como as respostas são determinísticas, gravar duas vezes produz arquivos idênticos.

## Política de mudança

- Acréscimo compatível (campo novo, rota nova, valor novo de enumeração) sobe a versão
  secundária (1.1.0) e é avisado ao agente.
- Remover ou renomear rota, parâmetro ou campo, ou mudar seu tipo ou significado, sobe a versão
  principal (2.0.0) e exige combinar com o agente antes.
