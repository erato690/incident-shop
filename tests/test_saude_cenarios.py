JANELAS = {
    "pool_esgotado": ("pedidos-api", "2026-10-06T14:00:00-03:00", "2026-10-06T13:30:00-03:00", "2026-10-06T14:30:00-03:00"),
    "banco_lento_com_deploy": ("pedidos-api", "2026-10-08T15:47:00-03:00", "2026-10-08T15:15:00-03:00", "2026-10-08T16:15:00-03:00"),
    "deploy_com_bug": ("pagamentos-api", "2026-10-14T14:38:00-03:00", "2026-10-14T14:15:00-03:00", "2026-10-14T15:05:00-03:00"),
    "env_var_faltando": ("estoque-worker", "2026-10-19T16:21:00-03:00", "2026-10-19T16:00:00-03:00", "2026-10-19T16:45:00-03:00"),
    "certificado_expirado": ("auth-api", "2026-10-23T21:00:00-03:00", "2026-10-23T20:30:00-03:00", "2026-10-23T21:30:00-03:00"),
    "vazamento_memoria": ("auth-api", "2026-10-27T12:05:00-03:00", "2026-10-27T11:15:00-03:00", "2026-10-27T12:55:00-03:00"),
    "gateway_fora": ("pagamentos-api", "2026-10-29T09:10:00-03:00", "2026-10-29T08:50:00-03:00", "2026-10-29T10:40:00-03:00"),
    "rate_limit": ("pagamentos-api", "2026-10-30T20:05:00-03:00", "2026-10-30T19:45:00-03:00", "2026-10-30T20:30:00-03:00"),
}


def test_saude(client):
    r = client.get("/saude")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "fonte": "simulada", "versao_contrato": "1.0.0"}


def test_cenarios_lista_os_oito_com_janelas(client):
    corpo = client.get("/cenarios").json()
    assert [c["id"] for c in corpo["cenarios"]] == list(JANELAS)
    for c in corpo["cenarios"]:
        servico, sintoma, ini, fim = JANELAS[c["id"]]
        assert set(c) == {"id", "titulo", "servico", "sintoma_inicio", "janela"}
        assert c["servico"] == servico and c["titulo"]
        assert c["sintoma_inicio"] == sintoma
        assert c["janela"] == {"inicio": ini, "fim": fim}


def test_cenarios_nao_expoe_causa_raiz(client):
    texto = client.get("/cenarios").text
    assert "causa_raiz" not in texto and "gabarito" not in texto and "Nenhuma mudança" not in texto


def test_rotas_antigas_removidas(client):
    assert client.post("/cenarios/pool_esgotado").status_code == 404
    assert all(m == {"GET"} for m in [r.methods - {"HEAD", "OPTIONS"} for r in client.app.routes if r.path in {"/logs", "/metricas", "/deploys", "/saude", "/cenarios"}])


TERMOS_CAUSA = ["nullpointer", "variável", "certificado", "tls", "vazamento", "oom", "rate limit",
                "distração", "deploy", "pool", "gateway", "reindex"]


def test_titulos_neutros_sem_causa_raiz(client):
    for c in client.get("/cenarios").json()["cenarios"]:
        assert not [t for t in TERMOS_CAUSA if t in c["titulo"].lower()], c["titulo"]
