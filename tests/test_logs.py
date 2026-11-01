import pytest

SINAIS = [
    ("pool_esgotado", "pedidos-api", "ERROR", "HikariPool-1 - Connection is not available"),
    ("banco_lento_com_deploy", "pedidos-api", "ERROR", "PSQLException"),
    ("banco_lento_com_deploy", "estoque-worker", "ERROR", "statement timeout"),
    ("banco_lento_com_deploy", "estoque-worker", "WARN", "reindexação da tabela estoque em andamento no db-principal"),
    ("banco_lento_com_deploy", "estoque-worker", "WARN", "REINDEX TABLE estoque"),
    ("deploy_com_bug", "pagamentos-api", "ERROR", "NullPointerException"),
    ("deploy_com_bug", "pagamentos-api", "ERROR", "Cupom.getDesconto()"),
    ("deploy_com_bug", "pedidos-api", "WARN", "respondeu 500"),
    ("env_var_faltando", "estoque-worker", "ERROR", "KeyError: 'ESTOQUE_QUEUE_URL'"),
    ("certificado_expirado", "auth-api", "ERROR", "CERTIFICATE_VERIFY_FAILED"),
    ("certificado_expirado", "auth-api", "ERROR", "idp.loja.internal"),
    ("vazamento_memoria", "auth-api", "ERROR", "OOMKilled"),
    ("vazamento_memoria", "auth-api", "WARN", "GC overhead"),
    ("gateway_fora", "pagamentos-api", "ERROR", "SocketTimeoutException"),
    ("gateway_fora", "pagamentos-api", "ERROR", "HTTP 503 Service Unavailable"),
    ("rate_limit", "pagamentos-api", "WARN", "429 Too Many Requests"),
    ("rate_limit", "pagamentos-api", "WARN", "X-RateLimit-Limit: 100/min"),
]


def logs(client, **p):
    r = client.get("/logs", params=p)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.parametrize("cenario,servico,nivel,trecho", SINAIS)
def test_sinal_do_cenario(client, cenario, servico, nivel, trecho):
    corpo = logs(client, cenario=cenario, servico=servico, nivel=nivel, limite=5000)
    assert any(trecho in l["mensagem"] for l in corpo["logs"])


def test_formato_do_log(client):
    corpo = logs(client, cenario="pool_esgotado", servico="pedidos-api", nivel="ERROR", limite=1)
    assert set(corpo) == {"consulta", "total", "truncado", "logs"}
    assert set(corpo["logs"][0]) == {"horario", "servico", "nivel", "mensagem"}
    assert corpo["logs"][0]["horario"].endswith("-03:00")
    assert corpo["consulta"] == {
        "cenario": "pool_esgotado", "servico": "pedidos-api", "nivel": "ERROR",
        "inicio": "2026-10-06T13:30:00-03:00", "fim": "2026-10-06T14:30:00-03:00",
    }


def test_consulta_ecoa_nulos(client):
    c = logs(client, cenario="pool_esgotado")["consulta"]
    assert c["servico"] is None and c["nivel"] is None


def test_ordem_crescente_e_dentro_da_janela(client):
    hs = [l["horario"] for l in logs(client, cenario="deploy_com_bug", limite=5000)["logs"]]
    assert hs == sorted(hs) and hs[0] >= "2026-10-14T14:15:00-03:00" and hs[-1] < "2026-10-14T15:05:00-03:00"


def test_limite_truncado_e_total(client):
    todos = logs(client, cenario="pool_esgotado", nivel="ERROR", limite=5000)
    assert todos["truncado"] is False and todos["total"] == len(todos["logs"]) > 50
    um = logs(client, cenario="pool_esgotado", nivel="ERROR", limite=1)
    assert um["truncado"] is True and um["total"] == todos["total"] and len(um["logs"]) == 1
    assert um["logs"][0] == todos["logs"][0]


def test_limite_padrao_500(client):
    corpo = logs(client, inicio="2026-10-06T13:30:00", fim="2026-10-06T14:30:00", nivel="ERROR")
    assert len(corpo["logs"]) == min(500, corpo["total"])


def test_nivel_exato(client):
    corpo = logs(client, cenario="deploy_com_bug", nivel="WARN", limite=5000)
    assert corpo["logs"] and {l["nivel"] for l in corpo["logs"]} == {"WARN"}


def test_inicio_inclusivo_fim_exclusivo(client):
    corpo = logs(client, cenario="pool_esgotado", servico="pedidos-api", nivel="ERROR", limite=5000)
    h0 = corpo["logs"][0]["horario"]
    de = logs(client, inicio=h0, fim="2026-10-06T14:30:00-03:00", servico="pedidos-api", nivel="ERROR", limite=5000)
    assert de["logs"][0]["horario"] == h0
    ate = logs(client, inicio="2026-10-06T13:30:00-03:00", fim=h0, servico="pedidos-api", nivel="ERROR", limite=5000)
    assert ate["total"] == 0


def test_janela_explicita_sem_fuso(client):
    a = logs(client, inicio="2026-10-06T14:00:00", fim="2026-10-06T14:05:00", servico="pedidos-api", nivel="ERROR")
    b = logs(client, inicio="2026-10-06T14:00:00-03:00", fim="2026-10-06T14:05:00-03:00", servico="pedidos-api", nivel="ERROR")
    assert a == b and a["total"] > 0


def test_janela_explicita_vale_sobre_cenario(client):
    c = logs(client, cenario="pool_esgotado", inicio="2026-10-06T14:00:00", fim="2026-10-06T14:10:00")
    assert c["consulta"]["inicio"] == "2026-10-06T14:00:00-03:00"
    assert c["consulta"]["fim"] == "2026-10-06T14:10:00-03:00"
    assert c["consulta"]["cenario"] == "pool_esgotado"


def test_saudavel_fora_de_incidente(client):
    corpo = logs(client, inicio="2026-11-01T10:00:00", fim="2026-11-01T11:00:00", limite=5000)
    assert 0 < corpo["total"] <= 60
    assert {l["nivel"] for l in corpo["logs"]} == {"INFO"}


def test_sintoma_nao_aparece_antes(client):
    corpo = logs(client, inicio="2026-10-06T13:30:00", fim="2026-10-06T14:00:00", nivel="ERROR")
    assert corpo["total"] == 0


def test_cenario_desconhecido_404(client):
    r = client.get("/logs", params={"cenario": "nao_existe"})
    assert r.status_code == 404 and isinstance(r.json()["detail"], str)


@pytest.mark.parametrize("p", [
    {},
    {"inicio": "2026-10-06T13:30:00"},
    {"fim": "2026-10-06T13:30:00"},
    {"cenario": "pool_esgotado", "servico": "outro-api"},
    {"cenario": "pool_esgotado", "nivel": "DEBUG"},
    {"cenario": "pool_esgotado", "nivel": "error"},
    {"cenario": "pool_esgotado", "limite": 0},
    {"cenario": "pool_esgotado", "limite": 5001},
    {"inicio": "2026-10-06T14:00:00", "fim": "2026-10-06T14:00:00"},
    {"inicio": "2026-10-06T15:00:00", "fim": "2026-10-06T14:00:00"},
    {"inicio": "2026-10-06T08:00:00", "fim": "2026-10-06T14:00:01"},
    {"inicio": "lixo", "fim": "2026-10-06T14:00:00"},
])
def test_422(client, p):
    r = client.get("/logs", params=p)
    assert r.status_code == 422 and isinstance(r.json()["detail"], list)
