"""Fatos citados nas conversas multi-turno do agente (spec, User Story 2)."""

HIKARI = (
    "HikariPool-1 - Connection is not available, request timed out after 3000ms "
    "(total=10, active=10, idle=0, waiting={n})\n"
    "\tat com.zaxxer.hikari.pool.HikariPool.createTimeoutException(HikariPool.java:696)\n"
    "\tat br.loja.pedidos.PedidoRepository.salvar(PedidoRepository.java:57)"
)


def get(client, rota, **p):
    r = client.get(rota, params=p)
    assert r.status_code == 200
    return r.json()


def serie(client, cenario, servico, metrica):
    return get(client, "/metricas", cenario=cenario, servico=servico, metrica=metrica)["series"][0]["pontos"]


# erro_investigado ---------------------------------------------------------

def test_erro_investigado_deploy(client):
    ds = get(client, "/deploys", cenario="pool_esgotado")["deploys"]
    assert len(ds) == 1
    assert (ds[0]["tag"], ds[0]["horario"], ds[0]["commit"]) == ("pedidos-api/v3.2.0", "2026-10-06T13:40:00-03:00", "a356b1f")
    todos = get(client, "/deploys")["deploys"]
    assert not any(d["versao"] == "3.8.1" for d in todos)


def test_erro_investigado_log_hikari_primeiro_erro(client):
    erros = get(client, "/logs", cenario="pool_esgotado", servico="pedidos-api", nivel="ERROR", limite=5000)["logs"]
    assert erros[0]["horario"].startswith("2026-10-06T14:00:")
    assert erros[0]["mensagem"] == HIKARI.format(n=41)
    assert all(e["horario"] >= "2026-10-06T14:00:00-03:00" for e in erros)
    esperado_prefixo = HIKARI.format(n="")[: HIKARI.index("waiting=") ]
    waitings = set()
    for e in erros:
        assert e["mensagem"].startswith(esperado_prefixo) and e["mensagem"].endswith(HIKARI.split(")", 1)[1])
        waitings.add(e["mensagem"].split("waiting=")[1].split(")")[0])
    assert len(waitings) > 5


def test_erro_investigado_log_de_deploy_com_pool_max(client):
    infos = get(client, "/logs", cenario="pool_esgotado", servico="pedidos-api", nivel="INFO", limite=5000)["logs"]
    deploy = [l for l in infos if "pool_max=10" in l["mensagem"]]
    assert len(deploy) == 1 and deploy[0]["horario"].startswith("2026-10-06T13:40:")
    assert "3.2.0" in deploy[0]["mensagem"]


def test_erro_investigado_antes_do_sintoma_saudavel(client):
    antes = get(client, "/logs", inicio="2026-10-06T13:30:00", fim="2026-10-06T14:00:00", nivel="ERROR")
    assert antes["total"] == 0


def test_erro_investigado_metricas(client):
    depois = "2026-10-06T14:00:00-03:00"
    for metrica, faixa in [("erros_5xx", (18, 40)), ("latencia_p95", (2500, 5200)), ("conexoes_db", (10, 10))]:
        v = [p["valor"] for p in serie(client, "pool_esgotado", "pedidos-api", metrica) if p["horario"] >= depois]
        assert len(v) == 30 and all(faixa[0] <= x <= faixa[1] for x in v), metrica


# escopo_externo -----------------------------------------------------------

def test_escopo_externo_sem_deploy_no_dia(client):
    assert get(client, "/deploys", cenario="gateway_fora")["deploys"] == []
    dia = get(client, "/deploys", inicio="2026-10-29T00:00:00", fim="2026-10-29T06:00:00")
    assert dia["deploys"] == []
    assert not any(d["horario"].startswith("2026-10-29") for d in get(client, "/deploys")["deploys"])


def test_escopo_externo_logs_do_pagamentos(client):
    erros = get(client, "/logs", cenario="gateway_fora", servico="pagamentos-api", nivel="ERROR", limite=5000)["logs"]
    assert erros[0]["horario"].startswith("2026-10-29T09:10:")
    assert erros[-1]["horario"] < "2026-10-29T10:20:00-03:00"
    msgs = " ".join(e["mensagem"] for e in erros)
    assert "java.net.SocketTimeoutException: Read timed out ao chamar https://api.pagafacil.com.br/v2/cobrancas" in msgs
    assert "HTTP 503 Service Unavailable" in msgs and "pagafacil" in msgs


def test_escopo_externo_pedidos_ve_502(client):
    warns = get(client, "/logs", cenario="gateway_fora", servico="pedidos-api", nivel="WARN", limite=5000)["logs"]
    assert warns and all("pagamentos-api respondeu 502 em POST /pagamentos" in w["mensagem"] for w in warns)
    assert warns[0]["horario"] >= "2026-10-29T09:10:00-03:00"


def test_escopo_externo_cpu_normal_e_erros_altos(client):
    cpu = [p["valor"] for p in serie(client, "gateway_fora", "pagamentos-api", "cpu")]
    assert max(cpu) - min(cpu) < 15 and max(cpu) < 45
    err = [p["valor"] for p in serie(client, "gateway_fora", "pagamentos-api", "erros_5xx") if "09:10" <= p["horario"][11:16] < "10:20"]
    assert len(err) == 70 and min(err) >= 20


def test_escopo_externo_normaliza_as_10h20(client):
    infos = get(client, "/logs", cenario="gateway_fora", servico="pagamentos-api", nivel="INFO", limite=5000)["logs"]
    normal = [l for l in infos if "normalizad" in l["mensagem"]]
    assert len(normal) == 1 and normal[0]["horario"].startswith("2026-10-29T10:20:")
    depois = get(client, "/logs", inicio="2026-10-29T10:20:00", fim="2026-10-29T10:40:00", servico="pagamentos-api", nivel="ERROR")
    assert depois["total"] == 0


def test_escopo_externo_pico_de_retentativas(client):
    req = {p["horario"][11:16]: p["valor"] for p in serie(client, "gateway_fora", "pagamentos-api", "requisicoes")}
    pico = [req[f"10:{m:02d}"] for m in range(20, 25)]
    depois = [req[f"10:{m:02d}"] for m in range(25, 40)]
    antes = [req[f"08:{m:02d}"] for m in range(50, 60)]
    assert min(pico) > 1.5 * max(depois) and max(depois) < 1.3 * min(antes) + 20
