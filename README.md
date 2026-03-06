# MVP Relatórios de Vendas (Django)

Projeto Django para dashboard e relatórios de vendas com gestão de acessos, staging de dados e exportação Excel.

## Setup

1. **Ambiente virtual e dependências**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```

2. **Banco de dados e admin**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

3. **Criar grupos e permissões**
   ```bash
   python manage.py setup_grupos
   ```
   Cria os grupos: admin, gestor, vendas, leitura (com permissões do app). Depois atribua usuários aos grupos no Admin.

4. **Importar CSV de vendas**
   ```bash
   # CSV com cabeçalho (colunas como VALORTOTAL, DATA_FATURAMENTO, etc.)
   python manage.py import_vendas_csv caminho/para/vendas.csv

   # Formato relatorio_fat (sem cabeçalho, vírgula) — coloque o CSV em dados/ e use:
   python manage.py import_vendas_csv dados/relatorio_fat.csv --format relatorio_fat --truncate
   ```
   Opções:
   - `--truncate` — apaga registros existentes antes de importar
   - `--format relatorio_fat` — CSV sem cabeçalho, mapeamento fixo por coluna
   - `--sep ";"` — separador (default: `;`; com relatorio_fat usa `,`)
   - `--encoding utf-8-sig` ou `latin-1` — encoding do arquivo
   - `--batch 5000` — tamanho do lote no bulk_create

   O comando normaliza:
   - decimais com vírgula → `Decimal`
   - datas pt-BR (ex: `01-fev-2024 00:00:00`) → `datetime`
   - códigos como `NUMPED`/`NUMNOTA` em string (evita notação científica)

5. **Rodar o servidor**
   ```bash
   python manage.py runserver
   ```
   - Login: http://127.0.0.1:8000/login/
   - Dashboard: http://127.0.0.1:8000/dashboard/
   - Relatório detalhado: http://127.0.0.1:8000/relatorio/
   - Admin: http://127.0.0.1:8000/admin/
   - **API dashboard (JSON):** GET `http://127.0.0.1:8000/api/dashboard/?data_inicio=2024-01-01&data_fim=2024-12-31` (requer sessão autenticada)

## Gestão de acessos

- **Grupos sugeridos:** admin, gestor, vendas, leitura (criar no Django Admin).
- **Permissões (app relatorios):**
  - `Pode ver relatório de vendas`
  - `Pode exportar Excel`
  - `Pode ver todas as filiais`
- **UserScope (Admin → Relatórios → Escopos):** por usuário, defina filiais e supervisores permitidos. Quem não tem “ver todas as filiais” só vê dados dentro do escopo.

## Estrutura principal

- `config/` — settings, urls do projeto
- `relatorios/` — app principal
  - `models.py` — UserScope, StgVendas
  - `services.py` — agregações e filtro por escopo
  - `views.py` — login, dashboard, relatório, export Excel
  - `export_excel.py` — geração xlsx com openpyxl
  - `utils_parse.py` — normalização pt-BR para o import
  - `management/commands/import_vendas_csv.py` — comando de importação

## Formato CSV esperado

Colunas compatíveis (nomes podem variar):  
`VALORTOTAL`, `VALOR_LIQUIDO`, `QTD`, `PESO`, `QTDEVOL`, `VALORBONIFICADO`, `DATA_FATURAMENTO`, `CODFILIAL`, `SUPERVISOR`, `SECAO`, `CATEGORIA`, `SUBCATEGORIA`, `CLIENTE`, `PRODUTO`, `NUMNOTA`, `NOMERCA`, `PTABELA`, `NUMPED`, etc.  
Separador padrão: `;`. Encoding recomendado: UTF-8 (com ou sem BOM).
