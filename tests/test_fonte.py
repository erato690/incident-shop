import pytest

from api.fontes import criar_fonte


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
