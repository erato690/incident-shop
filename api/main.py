"""API HTTP que simula logs, métricas e deploys da loja fictícia para o laboratório.

Expõe 4 endpoints: iniciar um cenário, consultar logs acumulados, consultar
métricas do minuto atual e listar o histórico (estático) de deploys.
"""

import zlib
from datetime import datetime, timezone
from random import Random

from fastapi import FastAPI, HTTPException

from api.cenarios import CENARIOS, Efeito

app = FastAPI(title="incident-shop")

# cache: dict[int minuto, Efeito]
_estado = {"cenario_id": None, "inicio": None, "cache": {}}

DEPLOYS = [
    {"servico": "pedidos-api", "tag": "pedidos-api/v3.1.0", "data": "2026-10-01T10:00:00-03:00", "commit": None, "mensagem": "estado inicial saudável (baseline)"},
    {"servico": "pagamentos-api", "tag": "pagamentos-api/v2.13.4", "data": "2026-10-12T10:00:00-03:00", "commit": None, "mensagem": "estado inicial saudável (baseline)"},
    {"servico": "estoque-worker", "tag": "estoque-worker/v1.5.2", "data": "2026-10-16T10:00:00-03:00", "commit": None, "mensagem": "estado inicial saudável (baseline)"},
    {"servico": "auth-api", "tag": "auth-api/v1.7.9", "data": "2026-10-22T10:00:00-03:00", "commit": None, "mensagem": "estado inicial saudável (baseline)"},
    {"servico": "pedidos-api", "tag": "pedidos-api/v3.2.0", "data": "2026-10-06T09:50:00-03:00", "commit": None, "mensagem": "reduz pool máximo de 20 para 10"},
    {"servico": "pedidos-api", "tag": "pedidos-api/v3.2.1", "data": "2026-10-08T15:40:00-03:00", "commit": "e90a4d7", "mensagem": "corrige texto do e-mail de confirmação"},
    {"servico": "pagamentos-api", "tag": "pagamentos-api/v2.14.0", "data": "2026-10-14T14:30:00-03:00", "commit": "a1f3c9e", "mensagem": "aplica desconto de cupom na confirmação do pagamento"},
    {"servico": "estoque-worker", "tag": "estoque-worker/v1.6.0", "data": "2026-10-19T16:15:00-03:00", "commit": "7bd0e21", "mensagem": "lê a URL da fila de uma variável de ambiente"},
    {"servico": "auth-api", "tag": "auth-api/v1.8.0", "data": "2026-10-27T11:20:00-03:00", "commit": "c44e8b0", "mensagem": "adiciona cache em memória sem limite para tokens validados"},
]


def _minuto_atual() -> int | None:
    """Minuto decorrido desde o início do cenário ativo, truncado na duração."""
    cenario_id = _estado["cenario_id"]
    if cenario_id is None:
        return None
    cenario = CENARIOS[cenario_id]
    decorridos = (datetime.now(timezone.utc) - _estado["inicio"]).total_seconds() // 60
    return min(int(decorridos), cenario.duracao - 1)


def _efeito_do_minuto(m: int) -> Efeito:
    """Calcula (e cacheia) o efeito do minuto m do cenário ativo."""
    cache = _estado["cache"]
    if m not in cache:
        cenario = CENARIOS[_estado["cenario_id"]]
        cache[m] = cenario.efeito(m, cenario.duracao, _estado["rng"])
    return cache[m]


@app.post("/cenarios/{cenario_id}", status_code=202)
def iniciar_cenario(cenario_id: str):
    cenario = CENARIOS.get(cenario_id)
    if cenario is None:
        raise HTTPException(status_code=404, detail=f"cenário '{cenario_id}' não existe")

    inicio = datetime.now(timezone.utc)
    _estado["cenario_id"] = cenario_id
    _estado["inicio"] = inicio
    _estado["cache"] = {}
    _estado["rng"] = Random(zlib.crc32(cenario_id.encode()))

    return {
        "cenario": cenario_id,
        "titulo": cenario.titulo,
        "duracao_min": cenario.duracao,
        "iniciado_em": inicio.isoformat(),
    }


@app.get("/logs")
def listar_logs():
    t = _minuto_atual()
    if t is None:
        return {"logs": []}

    logs = []
    for m in range(0, t + 1):
        efeito = _efeito_do_minuto(m)
        for servico, nivel, mensagem in efeito.logs:
            logs.append({"minuto": m, "servico": servico, "nivel": nivel, "mensagem": mensagem})
    return {"logs": logs}


@app.get("/metricas")
def listar_metricas():
    t = _minuto_atual()
    if t is None:
        return {"metricas": [
            {"servico": "pedidos-api", "metrica": "Erros5xx", "valor": 0},
            {"servico": "pedidos-api", "metrica": "LatenciaP95", "valor": 120},
        ]}

    efeito = _efeito_do_minuto(t)
    metricas = [
        {"servico": servico, "metrica": metrica, "valor": valor}
        for (servico, metrica), valor in efeito.metricas.items()
    ]
    return {"metricas": metricas}


@app.get("/deploys")
def listar_deploys():
    return {"deploys": DEPLOYS}
