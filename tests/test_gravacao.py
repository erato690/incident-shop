import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from scripts.gravar_dados_dummy import gravar  # noqa: E402


def test_grava_oito_arquivos_no_formato_do_contrato(tmp_path):
    ids = gravar(tmp_path)
    arquivos = sorted(p.name for p in tmp_path.glob("*.json"))
    assert len(arquivos) == 8
    assert arquivos == sorted(f"{i}.json" for i in ids)
    dados = json.loads((tmp_path / "pool_esgotado.json").read_text(encoding="utf-8"))
    assert list(dados) == ["cenario", "logs", "metricas", "deploys"]
    assert dados["cenario"]["id"] == "pool_esgotado"
    assert dados["logs"]["consulta"]["cenario"] == "pool_esgotado"


def test_nenhum_log_truncado(tmp_path):
    gravar(tmp_path)
    for arquivo in tmp_path.glob("*.json"):
        logs = json.loads(arquivo.read_text(encoding="utf-8"))["logs"]
        assert logs["truncado"] is False, f"{arquivo.name}: {logs['total']} logs passam de 5000"


def test_duas_gravacoes_sao_identicas(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    gravar(a)
    gravar(b)
    for arquivo in a.glob("*.json"):
        assert arquivo.read_bytes() == (b / arquivo.name).read_bytes()
    assert arquivo.read_bytes().endswith(b"\n")
