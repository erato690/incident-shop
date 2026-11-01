# incident-shop Constitution

Loja online fictícia (quatro serviços) e interface de programação de aplicações (API) HTTP que
fornece logs, métricas e deploys dos cenários de incidente consumidos pelo `incident-agent`.
Projeto de bloco "Agentes Cognitivos com LangChain" (Infnet). Entrega: 2026-11-09.

## Core Principles

### I. Escopo mínimo

- Só MUST ser construído o que a Fase 2 do `incident-agent` consome (logs, métricas e deploys
  por serviço, cenário e janela de tempo) ou o que deixa pronto o caminho da opção 2 (serviços
  reais) sem implementá-la.
- Funcionalidade sem consumidor no agente MUST NOT ser construída antes da entrega.
- Os quatro serviços reais rodando com `docker compose` (opção 2) ficam fora desta entrega:
  só o esqueleto documentado entra agora.

Razão: prazo curto; a API existe para servir o agente.

### II. Contrato estável

- O contrato da API (OpenAPI gerado pelo FastAPI e `docs/contrato-api.md` com exemplos) é a
  fonte da verdade para as ferramentas do agente.
- Mudança que quebra o contrato (remover ou renomear rota, campo ou parâmetro; mudar tipo ou
  significado) MUST NOT acontecer sem versão nova do contrato e aviso ao conductor.
- Acréscimo compatível (campo novo opcional, rota nova) MAY acontecer, com o documento
  atualizado no mesmo commit.
- Um teste de contrato MUST comparar o OpenAPI gerado com o arquivo versionado
  `docs/openapi.json`.
- As rotas MUST depender só da interface "fonte de dados"; a implementação simulada MUST poder
  ser trocada pela de serviços reais sem mudar o contrato.

Razão: o agente é construído em paralelo, em outra sessão, sobre este contrato.

### III. Dados coerentes e determinísticos

- Os dados de cada cenário MUST ser coerentes com as tags git, os commits e o README: versão,
  data e serviço de cada deploy MUST bater com a tag real.
- A mesma requisição MUST devolver a mesma resposta (sem relógio real nem aleatoriedade sem
  semente), para que o agente grave `dados_dummy/` reproduzíveis.
- Cenários com causa externa MUST NOT apontar deploy relacionado à causa.

Razão: o agente compara as tags pela API real do GitHub; incoerência gera conclusão errada.

### IV. Histórico git imutável

- As tags existentes e o histórico já publicado MUST NOT ser alterados nem reescritos.
- Commits novos são locais; push só com confirmação do Rafael.

Razão: o agente consulta o GitHub real; mudar tags quebra a comparação.

### V. Teste primeiro

- Cada comportamento da API MUST nascer de um teste que falha (pytest com `TestClient`).
- `pytest -q` MUST passar sem rede antes de declarar uma tarefa concluída.

Razão: o contrato só é estável se estiver coberto por testes.

## Segurança e entrega

- Chaves e segredos MUST NOT ir para o git; configuração vem de variáveis de ambiente.
- A imagem Docker MUST ler a porta da variável `PORT` (Railway).
- Ações públicas (push, deploy no Railway, publicar) MUST ter confirmação explícita do Rafael.
- Documentação, commits e respostas em português; siglas escritas por extenso na primeira
  ocorrência; a documentação MUST NOT citar aulas do curso.

## Fluxo de trabalho

- Planejamento com spec-kit: constitution, specify, clarify, plan, tasks; implementação com TDD.
- Decisões entre opções definidas são consultadas ao Jev (TypeSafe) e registradas com a
  confiança na spec.
- Quando o contrato mudar, o conductor MUST ser avisado para repassar à sessão do agente.

## Governance

- Esta constitution prevalece sobre outras práticas do repositório; planos MUST passar pelo
  Constitution Check do `/speckit-plan`.
- Emenda: proposta por escrito, aprovada pelo Rafael, com versão incrementada (MAJOR remove ou
  redefine princípio; MINOR adiciona princípio ou seção; PATCH corrige redação).

**Version**: 1.0.0 | **Ratified**: 2026-11-01 | **Last Amended**: 2026-11-01
