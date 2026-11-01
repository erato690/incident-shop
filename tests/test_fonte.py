from datetime import datetime

import pytest

from api.fontes import criar_fonte
from api.janela import TZ
from api.modelos import Ponto, RegistroLog, Resumo, SerieMetrica


def test_padrao_e_simulada(monkeypatch):
    monkeypatch.delenv("FONTE_DADOS", raising=False)
    assert criar_fonte().nome == "simulada"


def test_simulada_explicita(monkeypatch):
    monkeypatch.setenv("FONTE_DADOS", "simulada")
    assert criar_fonte().nome == "simulada"


def test_servicos_ainda_nao_existe(monkeypatch):
    monkeypatch.setenv("FONTE_DADOS", "servicos")
    with pytest.raises(NotImplementedError, match="docs/opcao2-servicos-reais.md"):
        criar_fonte()


def test_valor_desconhecido(monkeypatch):
    monkeypatch.setenv("FONTE_DADOS", "xyz")
    with pytest.raises(ValueError, match="FONTE_DADOS"):
        criar_fonte()


def test_metodos_de_servicos_explicam_a_opcao_2():
    from datetime import datetime

    from api.fontes.servicos import FonteServicos

    fonte, agora = FonteServicos(), datetime(2026, 10, 6)
    for chamada in (
        lambda: fonte.cenarios(),
        lambda: fonte.logs(None, None, agora, agora),
        lambda: fonte.metricas(None, None, agora, agora),
        lambda: fonte.deploys(None, None, None),
    ):
        with pytest.raises(NotImplementedError, match="opcao2-servicos-reais"):
            chamada()


class FonteFalsa:
    nome = "falsa"

    def cenarios(self):
        from api.modelos import CenarioPublico, Janela

        t0, t1 = datetime(2026, 1, 1, 10, tzinfo=TZ), datetime(2026, 1, 1, 11, tzinfo=TZ)
        return [CenarioPublico(id="x", titulo="X", servico="auth-api", sintoma_inicio=t0, janela=Janela(inicio=t0, fim=t1))]

    def logs(self, servico, nivel, inicio, fim):
        return [RegistroLog(horario=inicio, servico="auth-api", nivel="INFO", mensagem="da fonte falsa")]

    def metricas(self, servico, metrica, inicio, fim):
        resumo = Resumo(min=1, max=1, media=1, ultimo=1)
        return [SerieMetrica(servico="auth-api", metrica="cpu", unidade="%", resumo=resumo,
                             pontos=[Ponto(horario=inicio, valor=1)])]

    def deploys(self, servico, inicio, fim):
        return []


def test_fonte_falsa_responde_pelas_mesmas_rotas(client):
    from api.main import app, obter_fonte

    app.dependency_overrides[obter_fonte] = lambda: FonteFalsa()
    try:
        assert client.get("/saude").json()["fonte"] == "falsa"
        assert client.get("/cenarios").json()["cenarios"][0]["id"] == "x"
        logs = client.get("/logs", params={"cenario": "x"}).json()
        assert (logs["total"], logs["logs"][0]["mensagem"]) == (1, "da fonte falsa")
        assert client.get("/metricas", params={"cenario": "x"}).json()["series"][0]["metrica"] == "cpu"
        assert client.get("/deploys", params={"cenario": "x"}).json()["deploys"] == []
        assert client.get("/logs", params={"cenario": "outro"}).status_code == 404
    finally:
        app.dependency_overrides.clear()
