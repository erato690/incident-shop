import pytest

UNIDADES = {
    "requisicoes": "req/min", "erros_5xx": "erros/min", "latencia_p95": "ms", "cpu": "%",
    "memoria": "%", "reinicios": "reinícios/min", "conexoes_db": "conexões", "fila_mensagens": "mensagens",
}


def metricas(client, **p):
    r = client.get("/metricas", params=p)
    assert r.status_code == 200, r.text
    return r.json()


def serie(client, cenario, servico, metrica):
    s = metricas(client, cenario=cenario, servico=servico, metrica=metrica)["series"]
    assert len(s) == 1
    return s[0]


def valores(s, de=None, ate=None):
    return [p["valor"] for p in s["pontos"] if (de is None or p["horario"] >= de) and (ate is None or p["horario"] < ate)]


def test_um_ponto_por_minuto_e_formato(client):
    corpo = metricas(client, cenario="pool_esgotado", servico="pedidos-api", metrica="conexoes_db")
    assert corpo["consulta"] == {
        "cenario": "pool_esgotado", "servico": "pedidos-api", "metrica": "conexoes_db",
        "inicio": "2026-10-06T13:30:00-03:00", "fim": "2026-10-06T14:30:00-03:00",
    }
    s = corpo["series"][0]
    assert set(s) == {"servico", "metrica", "unidade", "resumo", "pontos"}
    assert s["unidade"] == "conexões" and len(s["pontos"]) == 60
    assert s["pontos"][0] == {"horario": "2026-10-06T13:30:00-03:00", "valor": s["pontos"][0]["valor"]}
    assert s["pontos"][1]["horario"] == "2026-10-06T13:31:00-03:00"
    assert s["pontos"][-1]["horario"] == "2026-10-06T14:29:00-03:00"


def test_resumo_coerente(client):
    s = serie(client, "pool_esgotado", "pedidos-api", "conexoes_db")
    v = valores(s)
    r = s["resumo"]
    assert r["min"] == min(v) and r["max"] == max(v) and r["ultimo"] == v[-1]
    assert r["media"] == pytest.approx(sum(v) / len(v), abs=0.06)


def test_todas_as_series(client):
    corpo = metricas(client, cenario="pool_esgotado")
    pares = {(s["servico"], s["metrica"]) for s in corpo["series"]}
    assert len(pares) == len(corpo["series"]) == 27
    assert ("auth-api", "conexoes_db") not in pares and ("pedidos-api", "fila_mensagens") not in pares
    assert ("estoque-worker", "fila_mensagens") in pares
    assert {s["metrica"]: s["unidade"] for s in corpo["series"]} == UNIDADES


def test_servico_sem_a_metrica_devolve_vazio(client):
    assert metricas(client, cenario="pool_esgotado", servico="auth-api", metrica="conexoes_db")["series"] == []


def test_pool_esgotado(client):
    cdb = serie(client, "pool_esgotado", "pedidos-api", "conexoes_db")
    assert max(valores(cdb, ate="2026-10-06T14:00:00-03:00")) <= 7
    assert set(valores(cdb, de="2026-10-06T14:00:00-03:00")) == {10.0}
    lat = serie(client, "pool_esgotado", "pedidos-api", "latencia_p95")
    assert all(2500 <= x <= 5200 for x in valores(lat, de="2026-10-06T14:00:00-03:00"))
    assert max(valores(lat, ate="2026-10-06T14:00:00-03:00")) < 500
    err = serie(client, "pool_esgotado", "pedidos-api", "erros_5xx")
    assert all(18 <= x <= 40 for x in valores(err, de="2026-10-06T14:00:00-03:00"))
    assert max(valores(err, ate="2026-10-06T14:00:00-03:00")) <= 2
    req = serie(client, "pool_esgotado", "pedidos-api", "requisicoes")
    antes = valores(req, ate="2026-10-06T13:35:00-03:00")
    depois = valores(req, de="2026-10-06T14:00:00-03:00")
    assert min(depois) > 1.3 * 140 and sum(valores(req, ate="2026-10-06T14:00:00-03:00")[-5:]) > sum(antes)


def test_banco_lento(client):
    lat = serie(client, "banco_lento_com_deploy", "estoque-worker", "latencia_p95")
    assert min(valores(lat, de="2026-10-08T15:47:00-03:00", ate="2026-10-08T16:12:00-03:00")) >= 2000
    assert max(valores(lat, ate="2026-10-08T15:47:00-03:00")) < 500


def test_deploy_com_bug(client):
    err = serie(client, "deploy_com_bug", "pagamentos-api", "erros_5xx")
    assert all(25 <= x <= 45 for x in valores(err, de="2026-10-14T14:38:00-03:00", ate="2026-10-14T15:03:00-03:00"))
    assert max(valores(err, ate="2026-10-14T14:38:00-03:00")) <= 2


def test_env_var_faltando(client):
    req = serie(client, "env_var_faltando", "estoque-worker", "requisicoes")
    assert set(valores(req, de="2026-10-19T16:21:00-03:00", ate="2026-10-19T16:41:00-03:00")) == {0.0}
    assert min(valores(req, ate="2026-10-19T16:20:00-03:00")) > 30
    fila = valores(serie(client, "env_var_faltando", "estoque-worker", "fila_mensagens"), de="2026-10-19T16:21:00-03:00", ate="2026-10-19T16:41:00-03:00")
    assert fila == sorted(fila) and fila[-1] - fila[0] >= 19 * 100
    rein = serie(client, "env_var_faltando", "estoque-worker", "reinicios")
    assert all(x > 0 for x in valores(rein, de="2026-10-19T16:21:00-03:00", ate="2026-10-19T16:41:00-03:00"))


def test_certificado_expirado(client):
    err = serie(client, "certificado_expirado", "auth-api", "erros_5xx")
    assert min(valores(err, de="2026-10-23T21:00:00-03:00", ate="2026-10-23T21:30:00-03:00")) >= 40


def test_vazamento_memoria(client):
    mem = serie(client, "vazamento_memoria", "auth-api", "memoria")
    assert 50 <= valores(mem)[0] <= 60
    cresce = valores(mem, de="2026-10-27T11:25:00-03:00", ate="2026-10-27T12:05:00-03:00")
    assert cresce[-1] > cresce[0] + 30 and cresce[-1] >= 90
    rein = serie(client, "vazamento_memoria", "auth-api", "reinicios")
    assert sum(valores(rein, ate="2026-10-27T12:05:00-03:00")) == 0
    assert sum(1 for x in valores(rein, de="2026-10-27T12:05:00-03:00") if x > 0) >= 3
    assert valores(rein, de="2026-10-27T12:05:00-03:00")[0] > 0


def test_vazamento_memoria_saudavel_apos_sintoma_fim(client):
    de, ate = "2026-10-27T12:53:00-03:00", "2026-10-27T12:55:00-03:00"
    rein = serie(client, "vazamento_memoria", "auth-api", "reinicios")
    assert sum(valores(rein, de=de, ate=ate)) == 0
    mem = serie(client, "vazamento_memoria", "auth-api", "memoria")
    assert max(valores(mem, de=de, ate=ate)) <= 62
    r = client.get("/logs", params={"cenario": "vazamento_memoria", "servico": "auth-api",
                                    "inicio": de, "fim": ate, "limite": 5000})
    assert not any("OOMKilled" in l["mensagem"] or "GC overhead" in l["mensagem"] for l in r.json()["logs"])


def test_gateway_fora(client):
    cpu = serie(client, "gateway_fora", "pagamentos-api", "cpu")
    assert max(valores(cpu)) < 45 and min(valores(cpu)) > 15
    err = serie(client, "gateway_fora", "pagamentos-api", "erros_5xx")
    assert all(x >= 20 for x in valores(err, de="2026-10-29T09:10:00-03:00", ate="2026-10-29T10:20:00-03:00"))
    assert max(valores(err, de="2026-10-29T10:25:00-03:00")) <= 2
    lat = serie(client, "gateway_fora", "pagamentos-api", "latencia_p95")
    assert min(valores(lat, de="2026-10-29T09:10:00-03:00", ate="2026-10-29T10:20:00-03:00")) >= 3000
    assert max(valores(lat, de="2026-10-29T10:25:00-03:00")) < 500
    req = serie(client, "gateway_fora", "pagamentos-api", "requisicoes")
    pico = valores(req, de="2026-10-29T10:20:00-03:00", ate="2026-10-29T10:25:00-03:00")
    normal = valores(req, de="2026-10-29T10:25:00-03:00")
    assert min(pico) > 1.5 * max(normal)


def test_rate_limit(client):
    req = serie(client, "rate_limit", "pagamentos-api", "requisicoes")
    assert all(200 <= x <= 250 for x in valores(req, de="2026-10-30T20:05:00-03:00", ate="2026-10-30T20:25:00-03:00"))
    assert max(valores(req, ate="2026-10-30T20:05:00-03:00")) < 130


@pytest.mark.parametrize("p", [
    {"cenario": "pool_esgotado", "metrica": "disco"},
    {"cenario": "pool_esgotado", "servico": "outro-api"},
    {"metrica": "cpu"},
    {"inicio": "2026-10-06T08:00:00", "fim": "2026-10-06T14:30:00"},
])
def test_422(client, p):
    assert client.get("/metricas", params=p).status_code == 422


def test_404(client):
    assert client.get("/metricas", params={"cenario": "x"}).status_code == 404


def test_saudavel_baseline_estavel(client):
    corpo = metricas(client, inicio="2026-11-01T10:00:00", fim="2026-11-01T10:30:00", servico="pedidos-api", metrica="erros_5xx")
    assert max(valores(corpo["series"][0])) <= 2
