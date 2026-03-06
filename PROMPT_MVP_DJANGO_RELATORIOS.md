# Prompt único: gerar esqueleto do MVP Django Relatórios

Copie o bloco abaixo e use no Cursor (Composer) para gerar o projeto inteiro em etapas ou de uma vez.

---

## TEXTO DO PROMPT (copiar da linha abaixo)

```
Crie um projeto Django (MVP que vira produto) com o seguinte escopo:

## 1) Gestão de acessos
- Usar usuários e grupos do Django (admin, gestor, vendas, leitura).
- Permissões por relatório: "Pode ver relatório de vendas", "Pode exportar Excel", "Pode ver todas as filiais" vs "Somente minha filial".
- Modelo UserScope: filiais permitidas e supervisores permitidos por usuário (FK para usuário, campos para CODFILIAL e SUPERVISOR quando aplicável).

## 2) Modelo de dados (staging)
- Tabela staging: stg_vendas (Postgres ou SQLite para dev), com campos compatíveis com CSV de vendas:
  VALORTOTAL, VALOR_LIQUIDO, QTD, PESO, QTDEVOL, VALORBONIFICADO, DATA_FATURAMENTO, CODFILIAL, SUPERVISOR, SECAO, CATEGORIA, SUBCATEGORIA, CLIENTE, PRODUTO, NUMNOTA, NOMERCA, PTABELA, NUMPED, etc.
- Tipos: datas como DateTimeField, valores como DecimalField, códigos/IDs como CharField (evitar notação científica).
- Comando management: import_vendas_csv que:
  - Lê CSV com encoding e separador adequados.
  - Normaliza pt-BR: vírgula → decimal, datas "01-fev-2024 00:00:00", NUMPED como string para não virar científico.
  - Faz bulk_create em stg_vendas (com truncate/delete antes se desejado).

## 3) Métricas e telas
- Dashboard:
  - Filtros: período, filial, supervisor, seção/categoria (respeitando UserScope do usuário).
  - Cards (KPIs): Total vendido, Qtd itens, Peso total, Devolução, Bonificação, Ticket médio (Total / nº notas).
  - 2 a 4 gráficos: série temporal (dia/mês), top 10 produtos, vendas por filial, por supervisor ou mix seção/categoria.
- Relatório detalhado: tabela paginada com busca e botão "Exportar Excel".
- Admin Django: usuários, grupos, UserScope (filiais/supervisores permitidos).

## 4) Stack e regras técnicas
- Django + Django REST Framework para APIs de agregação (cards e séries).
- Front: templates Django + HTMX (ou preparar endpoints para SPA depois). Gráficos: Chart.js ou ECharts. Export Excel: openpyxl (xlsx) com filtros e checagem de permissão "Pode exportar Excel".
- No import e nas queries, tratar sempre: decimais com vírgula, datas pt-BR, códigos como string.

## 5) Entregáveis
- Projeto Django configurado (settings, urls, requirements.txt).
- Modelos: UserScope, StgVendas (e UploadDataset opcional).
- Comando: python manage.py import_vendas_csv <caminho_csv>.
- Views/APIs: dashboard (cards + séries), relatório detalhado paginado, export Excel.
- Telas básicas: login, dashboard, relatório, admin.
- README com instruções de setup e uso do import.
```

---

## Como usar no Cursor

1. Abra o Composer (Ctrl+I ou Cmd+I).
2. Cole o texto do prompt acima (apenas o bloco entre as aspas triplas).
3. Se o projeto for grande, peça para fazer "por etapas": primeiro projeto + modelos, depois comando de import, depois APIs e telas.

Se quiser que eu gere o esqueleto direto no seu repositório, diga: "Gere o esqueleto do projeto aqui no ProjetoRelatorios".
