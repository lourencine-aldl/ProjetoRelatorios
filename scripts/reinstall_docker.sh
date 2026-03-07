#!/bin/bash
# Reinstala Docker e Docker Compose (Debian/Ubuntu)
# Execute como root: sudo bash scripts/reinstall_docker.sh

set -e

echo "=== Parando containers e removendo Docker ==="
docker compose -f /home/Projetos/Projeto-Django/docker-compose.yml down 2>/dev/null || true
systemctl stop docker.socket docker 2>/dev/null || true
apt-get remove -y docker-engine docker.io containerd runc docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin 2>/dev/null || true
apt-get purge -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin 2>/dev/null || true
rm -rf /var/lib/docker /var/lib/containerd /etc/docker
rm -f /etc/apt/sources.list.d/docker*.list

echo "=== Instalando dependências ==="
apt-get update
apt-get install -y ca-certificates curl gnupg

echo "=== Adicionando repositório Docker ==="
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
. /etc/os-release
if [ "$ID" = "debian" ]; then
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian ${VERSION_CODENAME:-bookworm} stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
else
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME:-jammy} stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
fi

echo "=== Instalando Docker Engine e Compose ==="
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "=== Iniciando e habilitando Docker ==="
systemctl start docker
systemctl enable docker

echo "=== Testando ==="
docker run --rm hello-world

echo ""
echo "Docker reinstalado. Suba o projeto:"
echo "  cd /home/Projetos/Projeto-Django && docker compose up -d"
