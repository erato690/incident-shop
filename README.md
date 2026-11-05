# loja-incidentes

Este é um repositório **fictício**, criado apenas para que o professor possa
validar o projeto de curso "agente investigador de incidentes" (AI Agents com
LangChain, Infnet). Os serviços das pastas `pedidos-api`, `pagamentos-api`,
`estoque-worker` e `auth-api` não rodam: seus arquivos são
pequenos e servem só para que o histórico git conte uma história coerente com
os cenários de incidente do laboratório. O agente consulta este repositório
pela API REST **real** do GitHub para descobrir o que mudou antes de um incidente.

## Serviços e dependências

O sistema simulado é uma loja online com quatro serviços, cada um em sua pasta:

- `pedidos-api`: recebe e cria pedidos. Chama o `pagamentos-api` para cobrar e
  publica reservas na fila consumida pelo `estoque-worker`. Usa o banco
  `db-principal`.
- `pagamentos-api`: confirma pagamentos e chama o gateway externo PagaFácil
  (que não é um serviço deste repositório; só aparece na configuração).
- `estoque-worker`: consome a fila `estoque-reservas` e atualiza a tabela
  `estoque` no `db-principal`.
- `auth-api`: emite e valida tokens, consultando o provedor de identidade
  `idp.loja.internal`.

## Tags

As tags seguem o padrão `<servico>/vX.Y.Z` e são anotadas. Cada serviço tem uma
tag base (estado saudável) e, quando o incidente tem causa em código ou
configuração versionada, uma tag posterior com o commit responsável. O agente
compara duas tags do mesmo serviço para ver a causa.

| Tag | Base de comparação | Cenário | O que mudou |
|---|---|---|---|
| `pedidos-api/v3.1.0` | - | (baseline) | pool de conexões em 20 |
| `pagamentos-api/v2.13.4` | - | (baseline) | estado saudável |
| `estoque-worker/v1.5.2` | - | (baseline) | estado saudável |
| `auth-api/v1.7.9` | - | (baseline) | estado saudável |
| `pagamentos-api/v2.14.0` | `pagamentos-api/v2.13.4` | `deploy_com_bug` | desconto de cupom aplicado sem checar `cupom == null` (NullPointerException) |
| `pedidos-api/v3.2.0` | `pedidos-api/v3.1.0` | `pool_esgotado` | `pool_max` reduzido de 20 para 10; o pico de tráfego esgota o pool |
| `estoque-worker/v1.6.0` | `estoque-worker/v1.5.2` | `env_var_faltando` | `ESTOQUE_QUEUE_URL` passa a ser obrigatória e sai do `.env.example` e do `config.yaml` |
| `auth-api/v1.8.0` | `auth-api/v1.7.9` | `vazamento_memoria` | cache em memória de tokens sem limite (OOMKilled) |
| `pedidos-api/v3.2.1` | `pedidos-api/v3.2.0` | `banco_lento_com_deploy` | **distração**: só corrige o texto do e-mail de confirmação |

## Cenários sem commit (causa externa)

Alguns cenários têm causa fora do código versionado, e por isso **não têm
commit nem tag** neste repositório. O agente deve concluir que não há mudança
relevante no GitHub e buscar a causa em logs e métricas:

- `gateway_fora`: o PagaFácil ficou indisponível (HTTP 503).
- `certificado_expirado`: o certificado TLS de `idp.loja.internal` expirou.
- `rate_limit`: o tráfego estourou o limite de 100 req/min do PagaFácil (o
  valor aparece em `pagamentos-api/config.yaml`, mas não foi alterado).
- `banco_lento_com_deploy`: a causa real é uma reindexação no `db-principal`.
  O deploy `pedidos-api/v3.2.1` é um **distrator deliberado**: a mudança é
  inofensiva (texto de e-mail) e ocorre perto do incidente para testar se o
  agente evita culpar o deploy errado.

## Endpoints usados pelo agente

- `GET /repos/{owner}/{repo}/compare/{base}...{head}` (ex.:
  `compare/pagamentos-api/v2.13.4...pagamentos-api/v2.14.0`)
- `GET /repos/{owner}/{repo}/tags`
- `GET /repos/{owner}/{repo}/commits`

Repositório público: **não é preciso token** (limite de 60 requisições por
hora por IP). Se a variável de ambiente `GITHUB_TOKEN` estiver definida, ela
pode ser usada para subir o limite, mas é opcional.

## Recriar o histórico

O histórico foi gerado de forma determinística (datas fixas em outubro de 2026) pelo script
`criar_repo.sh`, que não faz parte deste repositório.

## API HTTP

Além do histórico git, o repositório inclui uma interface de programação de aplicações (API)
HTTP em FastAPI (`api/`) que fornece logs, métricas e deploys da loja para os 8 cenários de
incidente. A API é **só de leitura** (todas as rotas são `GET`), **determinística** (a mesma
requisição devolve sempre o mesmo corpo, sem relógio real) e usa uma linha do tempo fixa de
outubro de 2026. Os deploys são os 9 reais do repositório (tag, commit, autor e mensagem
batem com o git). O agente pode consultá-la ao vivo ou usar dados gravados a partir dela.

Documentação:

- [`docs/contrato-api.md`](docs/contrato-api.md): contrato 1.1.0 com parâmetros, regras de
  janela, erros e exemplos.
- [`docs/openapi.json`](docs/openapi.json): especificação OpenAPI gerada pelo FastAPI; um teste
  garante que ela bate com a API.
- [`docs/opcao2-servicos-reais.md`](docs/opcao2-servicos-reais.md): como serviços reais
  responderiam pelas mesmas rotas (opção 2, ainda não implementada).

Rotas:

| Rota | O que devolve |
|---|---|
| `GET /saude` | Estado da API, fonte de dados e versão do contrato |
| `GET /cenarios` | Os 8 cenários com a janela de tempo de cada um (sem a causa raiz) |
| `GET /logs` | Logs por janela, com filtros `servico`, `nivel` e `limite` |
| `GET /metricas` | Séries de um ponto por minuto, com resumo, e filtros `servico` e `metrica` |
| `GET /deploys` | Deploys reais do repositório, com filtros `servico` e janela |
| `GET /estatisticas_banco` | Retrato do banco `db-principal` no início do sintoma do cenário (`cenario` obrigatório, filtro `servico`) |

A janela vem de `cenario` (id de `GET /cenarios`) ou do par `inicio` e `fim` (ISO 8601; sem
fuso vale `-03:00`; no máximo 6 horas). Exemplo:

```bash
curl -s 'localhost:8000/logs?cenario=pool_esgotado&servico=pedidos-api&nivel=ERROR&limite=1'
curl -s 'localhost:8000/deploys?cenario=pool_esgotado'
```

### Rodar localmente

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt   # inclui requirements.txt, pytest e httpx
uvicorn api.main:app --reload         # http://localhost:8000 (documentação interativa em /docs)
```

### Testes

```bash
pytest -q
```

Os testes rodam sem rede (usam o `TestClient` do FastAPI). Os que comparam deploys com o git
são pulados quando não há pasta `.git`; com ela, as tags dos serviços precisam existir.

### Gravar dados para o modo offline

```bash
python scripts/gravar_dados_dummy.py dados_dummy                       # app em processo
python scripts/gravar_dados_dummy.py dados_dummy --url http://localhost:8000
```

Grava `dados_dummy/<cenario>.json` (logs, métricas e deploys de cada cenário). Gravar duas vezes
produz arquivos idênticos. Se mudar rotas ou campos, atualize o OpenAPI com
`python scripts/exportar_openapi.py`.

### Docker e Railway

```bash
docker build -t incident-shop .
docker run --rm -e PORT=9000 -p 9000:9000 incident-shop   # a porta vem da variável PORT (padrão 8000)
curl -s localhost:9000/saude
```

A imagem usa `python:3.12-slim`, dependências fixadas e um usuário sem privilégio. O
`railway.toml` aponta para o `Dockerfile` e usa `/saude` como verificação de saúde; o Railway
define `PORT` em tempo de execução. O deploy público é feito **manualmente**, por decisão do
responsável; nada neste repositório publica a API sozinho.
