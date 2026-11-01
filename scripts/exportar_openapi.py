"""Grava docs/openapi.json a partir da aplicação (rode depois de mudar rotas, parâmetros ou campos)."""

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "docs" / "openapi.json"


def gerar_texto() -> str:
    """OpenAPI da aplicação como texto estável, com newline final."""
    from api.main import app

    return json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    DESTINO.write_text(gerar_texto(), encoding="utf-8")
    print(f"gravado {DESTINO.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(RAIZ))
    raise SystemExit(main())
