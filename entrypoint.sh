#!/bin/bash
set -e

echo "Aplicando migrações..."
python manage.py migrate --noinput

echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput --clear 2>/dev/null || true

exec "$@"
