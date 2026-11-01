def deploys(client, **p):
    r = client.get("/deploys", params=p)
    assert r.status_code == 200, r.text
    return r.json()


def test_sem_janela_devolve_todos(client):
    corpo = deploys(client)
    assert len(corpo["deploys"]) == 9
    assert corpo["consulta"] == {"cenario": None, "servico": None, "inicio": None, "fim": None}
    hs = [d["horario"] for d in corpo["deploys"]]
    assert hs == sorted(hs)


def test_formato(client):
    d = deploys(client, cenario="pool_esgotado")["deploys"][0]
    assert d == {
        "horario": "2026-10-06T13:40:00-03:00", "servico": "pedidos-api", "versao": "3.2.0",
        "tag": "pedidos-api/v3.2.0", "commit": "a356b1f", "autor": "Equipe Loja",
        "mensagem": "perf: reduz pool máximo de 20 para 10 para aliviar o db-principal",
    }


def test_consulta_ecoa_janela_do_cenario(client):
    assert deploys(client, cenario="pool_esgotado")["consulta"] == {
        "cenario": "pool_esgotado", "servico": None,
        "inicio": "2026-10-06T13:30:00-03:00", "fim": "2026-10-06T14:30:00-03:00",
    }


def test_deploy_suspeito_antes_do_sintoma(client):
    for cenario, tag, commit, hora in [
        ("pool_esgotado", "pedidos-api/v3.2.0", "a356b1f", "2026-10-06T13:40:00-03:00"),
        ("deploy_com_bug", "pagamentos-api/v2.14.0", "6245f86", "2026-10-14T14:35:00-03:00"),
        ("env_var_faltando", "estoque-worker/v1.6.0", "d5c8f27", "2026-10-19T16:20:00-03:00"),
        ("vazamento_memoria", "auth-api/v1.8.0", "7694861", "2026-10-27T11:25:00-03:00"),
    ]:
        ds = deploys(client, cenario=cenario)["deploys"]
        assert [(d["tag"], d["commit"], d["horario"]) for d in ds] == [(tag, commit, hora)]


def test_distrator_dois_minutos_antes_do_sintoma(client):
    ds = deploys(client, cenario="banco_lento_com_deploy")["deploys"]
    assert [(d["tag"], d["commit"], d["horario"]) for d in ds] == [
        ("pedidos-api/v3.2.1", "60b41c3", "2026-10-08T15:45:00-03:00")
    ]


def test_cenarios_externos_sem_deploy(client):
    for c in ("gateway_fora", "certificado_expirado", "rate_limit"):
        assert deploys(client, cenario=c)["deploys"] == []


def test_filtro_servico(client):
    ds = deploys(client, servico="auth-api")["deploys"]
    assert [d["tag"] for d in ds] == ["auth-api/v1.7.9", "auth-api/v1.8.0"]
    assert deploys(client, cenario="pool_esgotado", servico="auth-api")["deploys"] == []


def test_janela_explicita_inicio_inclusivo_fim_exclusivo(client):
    assert len(deploys(client, inicio="2026-10-06T13:40:00", fim="2026-10-06T14:00:00")["deploys"]) == 1
    assert deploys(client, inicio="2026-10-06T13:00:00", fim="2026-10-06T13:40:00")["deploys"] == []


def test_erros(client):
    assert client.get("/deploys", params={"cenario": "x"}).status_code == 404
    assert client.get("/deploys", params={"servico": "outro"}).status_code == 422
    assert client.get("/deploys", params={"inicio": "2026-10-06T15:00:00", "fim": "2026-10-06T14:00:00"}).status_code == 422
    assert client.get("/deploys", params={"inicio": "2026-10-01T00:00:00", "fim": "2026-10-30T00:00:00"}).status_code == 422
