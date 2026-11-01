FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ api/

# Usuário sem privilégio.
RUN useradd --system --no-create-home --uid 10001 loja
USER loja

EXPOSE 8000

# Forma shell para expandir ${PORT}: o Railway define PORT em tempo de execução.
CMD exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
