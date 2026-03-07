#!/bin/bash
# Rode no servidor (76.13.232.59) para verificar por que a página não carrega
# Uso: sudo bash scripts/verificar_servidor.sh

set -e
cd "$(dirname "$0")/.."

echo "=== 1. Container está rodando? ==="
docker ps -a --filter name=relatorios-web

echo ""
echo "=== 2. Porta 2026 está em uso? ==="
ss -tlnp | grep 2026 || true
netstat -tlnp 2>/dev/null | grep 2026 || true

echo ""
echo "=== 3. Últimos logs do container ==="
docker compose logs --tail=30 web 2>/dev/null || true

echo ""
echo "=== 4. Subir/recriar o container ==="
docker compose up -d

echo ""
echo "=== 5. Teste local (dentro do servidor) ==="
sleep 3
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:2026/ || echo "Falha ao conectar em 127.0.0.1:2026"

echo ""
echo "Se HTTP 200/302 = app OK. Se ainda não abrir no navegador, verifique FIREWALL:"
echo "  ufw allow 2026/tcp && ufw reload"
echo "  ou no painel do provedor: liberar porta TCP 2026"
