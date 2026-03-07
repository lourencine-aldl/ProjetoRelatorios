# ProjetoRelatorios - Deploy Docker
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependências do sistema (se precisar de libs para pandas/opencv etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Pastas para volume (SQLite e estáticos persistidos no compose)
RUN mkdir -p /app/staticfiles /app/media /app/db

EXPOSE 8000

# Entrypoint roda migrações, collectstatic e inicia o servidor
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "2", "config.wsgi:application"]
