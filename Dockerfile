FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ api/

ENV PORT=8000
EXPOSE 8000

# Shell form para permitir a expansão de ${PORT} (ex.: Railway define PORT em runtime).
CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
