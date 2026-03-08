# Abrir o projeto na web

## Com Docker (porta 2026)

O projeto sobe na **porta 2026**. Use uma das URLs abaixo.

**Se você está no mesmo computador do servidor:**
- http://127.0.0.1:2026/
- http://localhost:2026/

**Se você está em outro computador** (acessando um servidor remoto):
- http://IP_DO_SERVIDOR:2026/  
  (substitua `IP_DO_SERVIDOR` pelo IP ou domínio do servidor, ex.: `http://76.13.232.59:2026/`)

**Login:** admin / admin  
- [Login](http://127.0.0.1:2026/login/)
- [Admin Django](http://127.0.0.1:2026/admin/)
- [Dashboard](http://127.0.0.1:2026/dashboard/)

---

## Abrir pelo Cursor

1. Pressione **Ctrl+Shift+B** (ou Cmd+Shift+B no Mac) para abrir o Simple Browser.
2. Ou **Ctrl+Shift+P** → "Simple Browser: Show" → cole a URL.
3. Use **http://127.0.0.1:2026/** (se o Cursor está no mesmo servidor) ou **http://IP:2026/** (acesso remoto).

---

## Servidor não está rodando?

```bash
cd /home/Projetos/ProjetoRelatorios
docker compose up -d
```

Se a porta 2026 não abrir no navegador, verifique:
- **Firewall:** liberar a porta 2026 (ex.: `ufw allow 2026`).
- **URL correta:** com Docker use sempre a porta **2026**, não 8000.
