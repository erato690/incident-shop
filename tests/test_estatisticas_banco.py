from datetime import datetime

import pytest

from api.janela import TZ
from api.modelos import TabelaBanco

CENARIOS = [
    "pool_esgotado", "banco_lento_com_deploy", "deploy_com_bug", "env_var_faltando",
    "certificado_expirado", "vazamento_memoria", "gateway_fora", "rate_limit",
]
ORDEM = ["pedidos", "itens_pedido", "estoque", "reservas_estoque"]
CAMPOS = {
    "tabela", "servicos", "varreduras_sequenciais", "varreduras_por_indice", "reindexacao_em_andamento",
    "operacao_em_andamento", "ultimo_analyze", "inchaco_indice_pct",
}


def _get(client, **params):
    return client.get("/estatisticas_banco", params=params)


def test_formato(client):
    corpo = _get(client, cenario="banco_lento_com_deploy").json()
    assert set(corpo) == {"consulta", "banco", "tabelas"}
    assert corpo["banco"] == "db-principal"
    assert corpo["consulta"] == {
        "cenario": "banco_lento_com_deploy", "servico": None, "momento": "2026-10-08T15:47:00-03:00",
    }
    assert [t["tabela"] for t in corpo["tabelas"]] == ORDEM
    for t in corpo["tabelas"]:
        assert set(t) == CAMPOS
        assert isinstance(t["varreduras_sequenciais"], int) and isinstance(t["varreduras_por_indice"], int)
        assert isinstance(t["inchaco_indice_pct"], float)
        assert t["ultimo_analyze"].endswith("-03:00")


def test_servicos_por_tabela(client):
    t = {x["tabela"]: x["servicos"] for x in _get(client, cenario="rate_limit").json()["tabelas"]}
    assert t == {
        "pedidos": ["pedidos-api"], "itens_pedido": ["pedidos-api"],
        "estoque": ["pedidos-api", "estoque-worker"], "reservas_estoque": ["estoque-worker"],
    }


def test_sem_cenario_422(client):
    assert client.get("/estatisticas_banco").status_code == 422


def test_servico_invalido_422(client):
    assert _get(client, cenario="rate_limit", servico="xpto").status_code == 422


def test_cenario_desconhecido_404(client):
    assert _get(client, cenario="nao_existe").status_code == 404


def test_banco_lento_mostra_reindex_so_em_estoque(client):
    tabelas = {t["tabela"]: t for t in _get(client, cenario="banco_lento_com_deploy").json()["tabelas"]}
    est = tabelas["estoque"]
    assert est["reindexacao_em_andamento"] is True
    assert est["operacao_em_andamento"] == "REINDEX TABLE estoque"
    assert est["varreduras_sequenciais"] > 1000 and est["varreduras_por_indice"] < 100
    assert 40 <= est["inchaco_indice_pct"] <= 60
    for nome, t in tabelas.items():
        if nome != "estoque":
            assert t["reindexacao_em_andamento"] is False and t["operacao_em_andamento"] is None
            assert t["varreduras_por_indice"] >= 1000 and t["varreduras_sequenciais"] < 100
            assert 5 <= t["inchaco_indice_pct"] <= 20


@pytest.mark.parametrize("cenario", [c for c in CENARIOS if c != "banco_lento_com_deploy"])
def test_outros_cenarios_saudaveis(client, cenario):
    for t in _get(client, cenario=cenario).json()["tabelas"]:
        assert t["reindexacao_em_andamento"] is False and t["operacao_em_andamento"] is None
        assert t["varreduras_por_indice"] >= 1000 and t["varreduras_sequenciais"] < 100


def test_ultimo_analyze_na_madrugada_do_dia(client):
    for t in _get(client, cenario="banco_lento_com_deploy").json()["tabelas"]:
        assert t["ultimo_analyze"] == "2026-10-08T03:00:00-03:00"


def test_filtro_por_servico(client):
    def nomes(s):
        return [t["tabela"] for t in _get(client, cenario="banco_lento_com_deploy", servico=s).json()["tabelas"]]

    assert nomes("estoque-worker") == ["estoque", "reservas_estoque"]
    assert nomes("pedidos-api") == ["pedidos", "itens_pedido", "estoque"]
    assert nomes("pagamentos-api") == [] and nomes("auth-api") == []


def test_determinismo(client):
    assert _get(client, cenario="banco_lento_com_deploy").text == _get(client, cenario="banco_lento_com_deploy").text


def test_momento_e_sintoma_inicio(client):
    cenarios = {c["id"]: c for c in client.get("/cenarios").json()["cenarios"]}
    for id_, c in cenarios.items():
        assert _get(client, cenario=id_).json()["consulta"]["momento"] == c["sintoma_inicio"]


def test_fonte_falsa_cobre_a_rota(client):
    from api.main import app, obter_fonte
    class Falsa:
        nome = "falsa"

        def cenarios(self):
            from api.modelos import CenarioPublico, Janela

            t0, t1 = datetime(2026, 1, 1, 10, tzinfo=TZ), datetime(2026, 1, 1, 11, tzinfo=TZ)
            return [CenarioPublico(id="x", titulo="X", servico="auth-api", sintoma_inicio=t0, janela=Janela(inicio=t0, fim=t1))]

        def estatisticas_banco(self, cenario, servico):
            return [TabelaBanco(
                tabela="x", servicos=["auth-api"], varreduras_sequenciais=1, varreduras_por_indice=2,
                reindexacao_em_andamento=False, operacao_em_andamento=None,
                ultimo_analyze=datetime(2026, 1, 1, 3, tzinfo=TZ), inchaco_indice_pct=1.5,
            )]

    app.dependency_overrides[obter_fonte] = lambda: Falsa()
    try:
        corpo = _get(client, cenario="x").json()
        assert corpo["tabelas"][0]["tabela"] == "x" and corpo["consulta"]["momento"].startswith("2026-01-01T10")
        assert _get(client, cenario="y").status_code == 404
    finally:
        app.dependency_overrides.clear()
