import hashlib
import subprocess
import sys
from pathlib import Path

CONSULTAS = [
    ("/logs", {"cenario": "pool_esgotado", "limite": 5000}),
    ("/logs", {"cenario": "gateway_fora", "servico": "pagamentos-api", "limite": 5000}),
    ("/metricas", {"cenario": "vazamento_memoria"}),
    ("/metricas", {"cenario": "env_var_faltando", "servico": "estoque-worker"}),
    ("/deploys", {"cenario": "banco_lento_com_deploy"}),
    ("/cenarios", {}),
    ("/logs", {"inicio": "2026-11-01T10:00:00", "fim": "2026-11-01T12:00:00"}),
]


def corpo(client, rota, params):
    r = client.get(rota, params=params)
    assert r.status_code == 200
    return r.content


def test_mesma_consulta_corpo_identico(client):
    for rota, p in CONSULTAS:
        assert corpo(client, rota, p) == corpo(client, rota, p)


def test_ordem_das_consultas_nao_muda_corpo(client):
    direta = [corpo(client, r, p) for r, p in CONSULTAS]
    inversa = [corpo(client, r, p) for r, p in reversed(CONSULTAS)][::-1]
    assert direta == inversa


def test_valor_do_minuto_independe_da_janela(client):
    larga = client.get("/metricas", params={"cenario": "pool_esgotado", "servico": "pedidos-api", "metrica": "latencia_p95"}).json()
    estreita = client.get("/metricas", params={"inicio": "2026-10-06T14:10:00", "fim": "2026-10-06T14:20:00", "servico": "pedidos-api", "metrica": "latencia_p95"}).json()
    esperados = [p for p in larga["series"][0]["pontos"] if "14:10" <= p["horario"][11:16] < "14:20"]
    assert estreita["series"][0]["pontos"] == esperados


def test_outro_processo_mesmo_corpo(client):
    codigo = (
        "import hashlib;from fastapi.testclient import TestClient;from api.main import app;"
        "r=TestClient(app).get('/logs',params={'cenario':'pool_esgotado','limite':5000});"
        "print(hashlib.sha256(r.content).hexdigest())"
    )
    raiz = Path(__file__).resolve().parent.parent
    saida = subprocess.run([sys.executable, "-c", codigo], cwd=raiz, capture_output=True, text=True, check=True, env={"PYTHONHASHSEED": "random", "PATH": ""})
    esperado = hashlib.sha256(corpo(client, "/logs", CONSULTAS[0][1])).hexdigest()
    assert saida.stdout.strip() == esperado
