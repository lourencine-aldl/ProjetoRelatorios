# Deploy e execução

## Rodar localmente (sem Docker)

No seu PC, com Python 3.10+ instalado:

**Windows (PowerShell ou CMD):**
```cmd
scripts\run_local.bat
```

**Linux / Mac:**
```bash
bash scripts/run_local.sh
```

Na primeira vez o script cria o ambiente virtual (`venv`), instala dependências, aplica migrações e sobe o servidor em **http://127.0.0.1:8000/**.

- Página de teste: http://127.0.0.1:8000/teste/
- Login: http://127.0.0.1:8000/login/ (usuário **teste**, senha **123456**)

---

# Deploy com Docker

## Pré-requisitos

- Docker e Docker Compose instalados

## Uso rápido

```bash
# Criar arquivo de ambiente (opcional)
cp .env.example .env
# Edite .env e defina DJANGO_SECRET_KEY para produção

# Subir a aplicação
docker compose up -d

# Acessar: http://76.13.232.59:2026 (ou http://localhost:2026)
```

## Comandos úteis

```bash
# Ver logs
docker compose logs -f web

# Criar superusuário (após o container estar rodando)
docker compose exec web python manage.py createsuperuser

# Parar
docker compose down

# Parar e remover volumes (apaga banco e estáticos)
docker compose down -v
```

## Importar CSV de vendas (Relatorio_Fat)

O CSV deve ter cabeçalho na 1ª linha, separador vírgula e o formato do `Relatorio_Fat.csv`. Use o formato `relatorio_fat`:

```bash
# Com a pasta dados/ no host (monte no container)
docker compose run --rm -v $(pwd)/dados:/dados web python manage.py import_vendas_csv /dados/Relatorio_Fat.csv --format relatorio_fat --truncate --batch 5000
```

Sem Docker (com venv ativado):

```bash
python manage.py import_vendas_csv dados/Relatorio_Fat.csv --format relatorio_fat [--truncate] [--batch 5000]
```

## Variáveis de ambiente

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `DJANGO_SECRET_KEY` | Chave secreta do Django | (obrigatório em produção) |
| `DEBUG` | Modo debug (0 em produção) | 0 no compose |
| `ALLOWED_HOSTS` | Hosts permitidos (vírgula) | localhost,127.0.0.1,76.13.232.59 |
| `DATABASE_PATH` | Caminho do SQLite (Docker) | /app/db/db.sqlite3 |

## Volumes

- `db_data`: persiste o banco SQLite em `/app/db`
- `static_data`: persiste arquivos estáticos em `/app/staticfiles`

## Acesso não abre no navegador (alternativa: ngrok)

Se **http://76.13.232.59:2026/** não carregar (rede/firewall bloqueia), use um túnel:

1. No servidor, instale o [ngrok](https://ngrok.com): `curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list && sudo apt update && sudo apt install ngrok`
2. Crie conta em ngrok.com, pegue seu authtoken e configure: `ngrok config add-authtoken SEU_TOKEN`
3. Rode: `ngrok http 2026`
4. Use o link **https** que aparecer (ex.: `https://abc123.ngrok-free.app`) no navegador.
5. **Django:** para o ngrok funcionar, o domínio precisa estar em `ALLOWED_HOSTS`. No `.env` coloque: `ALLOWED_HOSTS=localhost,127.0.0.1,76.13.232.59,.ngrok-free.app,.ngrok.io` e rode `docker compose up -d --force-recreate`.

## Usar um nome (domínio) em vez do IP

1. **No seu provedor de domínio** (Registro.br, Hostinger, Cloudflare, etc.): crie um **registro A** ou **CNAME** apontando para o IP do servidor (`76.13.232.59`). Ex.: `relatorios.seudominio.com.br` → `76.13.232.59`.

2. **No servidor**, crie ou edite o `.env`:
   ```bash
   ALLOWED_HOSTS=localhost,127.0.0.1,76.13.232.59,relatorios.seudominio.com.br
   ```
   (troque `relatorios.seudominio.com.br` pelo nome que você criou.)

3. **Reinicie o container:**
   ```bash
   docker compose up -d --force-recreate
   ```

4. **Acesso:**
   - Com porta: **http://relatorios.seudominio.com.br:2026**
   - Para usar **sem porta** (só `http://relatorios.seudominio.com.br`), é preciso um proxy reverso (nginx) na porta 80; posso montar essa configuração se quiser.

## Produção (dicas)

1. Defina `DJANGO_SECRET_KEY` forte e único no `.env`.
2. Ajuste `ALLOWED_HOSTS` para seu domínio (veja seção acima).
3. Para tráfego alto, use um proxy reverso (nginx/Caddy) na frente do container e sirva `/static/` por ele.
4. Para muito volume de dados, considere PostgreSQL e variável `DATABASE_URL` (requer ajuste no `settings.py`).
