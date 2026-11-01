# Implementation Plan: Contrato da API da loja para a Fase 2 do agente

**Branch**: `001-contrato-api-fase2` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-contrato-api-fase2/spec.md`

## Summary

Trocar a API com estado (relógio real) por uma API sem estado, só leitura, que responde logs,
métricas e deploys da linha do tempo única da loja, com os 8 cenários em datas absolutas
coerentes com as tags git. As rotas dependem de uma interface `FonteDados`; a implementação
`FonteSimulada` é a padrão e `FonteServicos` (opção 2) fica como esqueleto. O contrato é o
OpenAPI gerado (`docs/openapi.json`, verificado por teste) e `docs/contrato-api.md`.

## Technical Context

**Language/Version**: Python 3.12 (imagem `python:3.12-slim`)
**Primary Dependencies**: FastAPI, Pydantic v2, Uvicorn; testes com pytest e httpx (`TestClient`)
**Storage**: N/A (dados gerados em memória de forma determinística)
**Testing**: pytest, sem rede
**Target Platform**: contêiner Linux (local e Railway)
**Project Type**: web-service
**Performance Goals**: resposta de uma janela de 6 horas em menos de 1 segundo
**Constraints**: determinístico; janela máxima 6 horas; `limite` de logs até 5000; porta `PORT`
**Scale/Scope**: 4 serviços, 8 cenários, 9 deploys, 5 rotas

## Constitution Check

| Princípio | Como o plano atende |
|---|---|
| I. Escopo mínimo | Só rotas de leitura que as ferramentas do agente usam; opção 2 só como esqueleto e documento |
| II. Contrato estável | Modelos Pydantic de resposta; `docs/openapi.json` + teste de contrato; rotas dependem só de `FonteDados` |
| III. Dados coerentes e determinísticos | Deploys copiados das tags reais (commit curto, autor); semente por cenário e minuto; sem relógio |
| IV. Histórico git imutável | Nenhuma tag criada ou alterada; commits locais |
| V. Teste primeiro | Cada tarefa começa por teste que falha |
| Segurança e entrega | Sem segredos; `PORT` no Dockerfile; deploy no Railway só com confirmação |

Resultado: sem violações.

## Project Structure

### Documentation (this feature)

```text
specs/001-contrato-api-fase2/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/README.md   # aponta para docs/contrato-api.md e docs/openapi.json
└── tasks.md
```

### Source Code (repository root)

```text
api/
├── main.py              # app FastAPI, rotas, dependência obter_fonte()
├── modelos.py           # modelos Pydantic de resposta (contrato)
├── janela.py            # resolução de janela (cenario, inicio, fim, fuso, limites)
├── fontes/
│   ├── __init__.py      # FonteDados (Protocol) e criar_fonte(FONTE_DADOS)
│   ├── simulada.py      # FonteSimulada: linha do tempo, baseline e efeitos
│   └── servicos.py      # FonteServicos: esqueleto da opção 2 (NotImplementedError)
├── cenarios.py          # catálogo dos 8 cenários (datas absolutas, efeitos por minuto)
└── deploys.py           # 9 deploys reais (tags, commits, autores)
scripts/exportar_openapi.py
tests/
├── test_saude_cenarios.py
├── test_logs.py
├── test_metricas.py
├── test_deploys.py
├── test_conversas.py    # fatos de erro_investigado e escopo_externo
├── test_determinismo.py
├── test_fonte.py        # injeção de fonte falsa, FONTE_DADOS
└── test_contrato.py     # OpenAPI gerado == docs/openapi.json; deploys == tags git
docs/
├── contrato-api.md
├── openapi.json
└── opcao2-servicos-reais.md
Dockerfile, railway.toml, requirements.txt, requirements-dev.txt
```

**Structure Decision**: projeto único; pacote `api/` existente, com a camada `fontes/` nova.

## Complexity Tracking

Sem violações a justificar.
