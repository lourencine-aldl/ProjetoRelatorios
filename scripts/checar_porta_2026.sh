#!/bin/bash
# Rode no servidor para checar por que 76.13.232.59:2026 não responde de fora
# Uso: bash scripts/checar_porta_2026.sh

echo "=== 1. Porta 2026 no host (deve mostrar 0.0.0.0:2026 ou *:2026) ==="
ss -tlnp | grep 2026 || true

echo ""
echo "=== 2. Teste DENTRO do servidor ==="
curl -s -o /dev/null -w "127.0.0.1:2026 -> HTTP %{http_code}\n" --connect-timeout 3 http://127.0.0.1:2026/ || echo "Falhou"
curl -s -o /dev/null -w "76.13.232.59:2026 -> HTTP %{http_code}\n" --connect-timeout 3 http://76.13.232.59:2026/ || echo "Falhou"

echo ""
echo "=== 3. Se acima der 200/302 mas no navegador não abre ==="
echo "   -> Firewall do PROVEDOR (Hostinger/OVH etc): abra a porta TCP 2026 no painel."
echo "   -> Use no navegador: http://76.13.232.59:2026/   (com http:// na frente)."
