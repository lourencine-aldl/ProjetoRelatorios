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

echo "Criando usuário admin (se não existir)..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    u = User.objects.create_user(username='admin', password='admin123')
    u.is_staff = True
    u.is_superuser = True
    u.save()
    print('Usuário admin criado (senha: admin123)')
else:
    print('Usuário admin já existe')
" 2>/dev/null || true

echo ""
echo "Servidor em: http://127.0.0.1:8000/"
echo "  Login: http://127.0.0.1:8000/login/  (admin / admin123)"
echo "  Admin: http://127.0.0.1:8000/admin/"
echo ""
python manage.py runserver 0.0.0.0:8000
