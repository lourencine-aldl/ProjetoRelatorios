#!/bin/bash
# Roda o projeto Django localmente (sem Docker)
# Uso: bash scripts/run_local.sh   ou   ./scripts/run_local.sh

set -e
cd "$(dirname "$0")/.."

echo "=== Ambiente local ==="
if [ ! -d "venv" ]; then
  echo "Criando venv..."
  python3 -m venv venv
fi
source venv/bin/activate

echo "Instalando dependências..."
pip install -q -r requirements.txt

echo "Aplicando migrações..."
python manage.py migrate --noinput

echo "Criando usuário teste (se não existir)..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='teste').exists():
    u = User.objects.create_user(username='teste', password='123456')
    u.is_staff = True
    u.is_superuser = True
    u.save()
    print('Usuário teste criado (senha: 123456)')
else:
    print('Usuário teste já existe')
" 2>/dev/null || true

echo ""
echo "Servidor em: http://127.0.0.1:8000/"
echo "  Teste: http://127.0.0.1:8000/teste/"
echo "  Login: http://127.0.0.1:8000/login/  (teste / 123456)"
echo ""
python manage.py runserver 0.0.0.0:8000
