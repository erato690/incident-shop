import shutil
import subprocess
from pathlib import Path

import pytest

from api.deploys import DEPLOYS

RAIZ = Path(__file__).resolve().parent.parent
TEM_GIT = shutil.which("git") is not None and (RAIZ / ".git").exists()


def _git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=True)
    return r.stdout.strip()


def test_nove_deploys_em_ordem():
    assert len(DEPLOYS) == 9
    horarios = [d.horario for d in DEPLOYS]
    assert horarios == sorted(horarios)


@pytest.mark.skipif(not TEM_GIT, reason="sem repositório git")
@pytest.mark.parametrize("d", DEPLOYS, ids=lambda d: d.tag)
def test_deploy_bate_com_git(d):
    commit = _git("rev-list", "-n1", d.tag)
    assert commit[:7] == d.commit
    assert _git("log", "-1", "--format=%an", commit) == d.autor
    assert _git("log", "-1", "--format=%s", commit) == d.mensagem
    assert d.tag == f"{d.servico}/v{d.versao}"


def test_openapi_igual_ao_arquivo():
    from scripts.exportar_openapi import DESTINO, gerar_texto

    esperado = DESTINO.read_text(encoding="utf-8") if DESTINO.exists() else ""
    assert gerar_texto() == esperado, (
        "docs/openapi.json está desatualizado: rode `python scripts/exportar_openapi.py` "
        "e versione o arquivo (mudança que quebra o contrato exige nova versão)."
    )


def test_openapi_identifica_o_contrato():
    from api.main import app

    info = app.openapi()["info"]
    assert (info["title"], info["version"]) == ("incident-shop", "1.0.0")
