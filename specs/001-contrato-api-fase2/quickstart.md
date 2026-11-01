# Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
uvicorn api.main:app --reload
curl -s localhost:8000/cenarios
curl -s 'localhost:8000/logs?cenario=pool_esgotado&servico=pedidos-api&nivel=ERROR&limite=3'
curl -s 'localhost:8000/deploys?cenario=pool_esgotado'
docker build -t incident-shop . && docker run --rm -e PORT=9000 -p 9000:9000 incident-shop
```
