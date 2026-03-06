#!/bin/bash
# Rode no servidor para ver por que o acesso externo não funciona
# Uso: bash scripts/diagnostico_acesso.sh

echo "=== 1. Container relatorios-web ==="
docker ps --filter name=relatorios-web --format "{{.Names}} {{.Status}}"

echo ""
echo "=== 2. Porta 2026 no host (deve mostrar 0.0.0.0:2026) ==="
ss -tlnp | grep 2026 || echo "Porta 2026 NÃO está em uso!"

echo ""
echo "=== 3. Teste local (dentro do servidor) ==="
CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 http://127.0.0.1:2026/ 2>/dev/null || echo "erro")
echo "curl http://127.0.0.1:2026/ -> HTTP $CODE"
if [ "$CODE" = "302" ] || [ "$CODE" = "200" ]; then
  echo "  -> App OK no servidor. Problema é rede/firewall entre você e o servidor."
fi

echo ""
echo "=== 4. Se ainda não abrir no seu navegador ==="
echo "  - Teste pelo 4G do celular: http://76.13.232.59:2026/"
echo "  - Ou use ngrok (túnel): ngrok http 2026   (gera um link que funciona)"
