"""Grava um arquivo JSON por cenário com as respostas da API (modo offline do agente).

Uso: python scripts/gravar_dados_dummy.py <pasta> [--url URL]
Sem --url usa a aplicação em processo (TestClient); com --url consulta a API por HTTP (httpx).
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Protocol

RAIZ = Path(__file__).resolve().parent.parent


class Cliente(Protocol):
    def get(self, url: str, **kwargs: Any) -> Any: ...


def _consultar(cliente: Cliente, rota: str, **params: Any) -> Any:
    resposta = cliente.get(rota, params=params)
    resposta.raise_for_status()
    return resposta.json()


def _montar(cliente: Cliente, item: dict) -> dict:
    cenario = item["id"]
    return {
        "cenario": item,
        "logs": _consultar(cliente, "/logs", cenario=cenario, limite=5000),
        "metricas": _consultar(cliente, "/metricas", cenario=cenario),
        "deploys": _consultar(cliente, "/deploys", cenario=cenario),
    }


def _serializar(dados: dict) -> str:
    return json.dumps(dados, ensure_ascii=False, indent=2) + "\n"


def gravar(pasta: Path, cliente: Cliente | None = None) -> list[str]:
    """Grava `<pasta>/<id>.json` para cada cenário e devolve os ids gravados."""
    if cliente is None:
        from fastapi.testclient import TestClient

        from api.main import app

        cliente = TestClient(app)
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    ids = []
    for item in _consultar(cliente, "/cenarios")["cenarios"]:
        dados = _montar(cliente, item)
        if dados["logs"]["truncado"]:
            print(f"aviso: logs de '{item['id']}' truncados ({dados['logs']['total']})", file=sys.stderr)
        (pasta / f"{item['id']}.json").write_text(_serializar(dados), encoding="utf-8")
        ids.append(item["id"])
    return ids


def main(argv: list[str] | None = None) -> int:
    analisador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analisador.add_argument("pasta", type=Path, help="pasta de destino dos arquivos <cenario>.json")
    analisador.add_argument("--url", help="URL base da API (padrão: aplicação em processo)")
    args = analisador.parse_args(argv)
    cliente = None
    if args.url:
        import httpx

        cliente = httpx.Client(base_url=args.url.rstrip("/"), timeout=30)
    ids = gravar(args.pasta, cliente)
    print(f"{len(ids)} cenários gravados em {args.pasta}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(RAIZ))
    raise SystemExit(main())
