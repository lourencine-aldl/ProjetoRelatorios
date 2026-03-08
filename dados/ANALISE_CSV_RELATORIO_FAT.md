# Análise do CSV Relatorio_Fat.csv (novo formato)

## Estrutura

- **Linhas:** 133.750 (1 cabeçalho + 133.749 registros)
- **Separador:** ponto e vírgula (`;`)
- **Cabeçalho:** primeira linha com nomes das colunas
- **Encoding:** UTF-8 (com acentos: Ã, Ç, etc.)

## Colunas (52 no total)

| Índice | Nome           | Exemplo / Observação        |
|--------|----------------|-----------------------------|
| 0      | CODFILIAL      | 1                           |
| 1      | DATA_FATURAMENTO | 02-jan-2026 00:00:00      |
| 5      | CLIENTE        | CASA DO BOLO MALTA...       |
| 12     | PRODUTO        | REQ CREM SAO VICENTE 1,5KG |
| 15     | QTD            | 3                           |
| 17     | PESO           | 4,71                        |
| 18     | PESOLIQ        | 4,5                         |
| 19     | VALORTOTAL     | 0 ou 173,2 (pt-BR)         |
| 22     | FORNECEDOR     | LATICINIOS SAO VICENTE...   |
| 24     | SUPERVISOR     | JULIO CESAR MANTA...        |
| 26     | NOMERCA        | JESSICA MATOS BATISTA       |
| 28     | SECAO          | RESFRIADOS                  |
| 34     | VALORBONIFICADO| 0                           |
| 35     | VLDEVOLUCAO    | 133,71                      |
| 37     | CATEGORIA      | LATICINIOS                  |
| 39     | SUBCATEGORIA   | REQUEIJAO CREMOSO           |
| 40     | VALOR_LIQUIDO  | 0 ou 15,67 (pt-BR)          |
| 45     | NUMNOTA        | 1584410                     |
| 46     | NUMPED         | 149050824                   |

Os índices batem com o `RELATORIO_FAT_MAP` do comando de importação.

## Diferenças em relação ao formato antigo

- **Antigo:** sem cabeçalho, separador vírgula (`,`), formato `relatorio_fat`.
- **Novo:** com cabeçalho, separador `;`. Deve ser importado **sem** `--format relatorio_fat`.

## Valores monetários

No novo CSV os valores aparecem em formato pt-BR (vírgula decimal), por exemplo:  
`15,67`; `173,2`; `133,71`; `1000`.  
Ou seja, já em reais. Se após a importação o “Total vendido” ficar 1000x menor que o esperado, configure no `.env`:

```bash
VALOR_DIVISOR=1
```

## Como importar

**Não use** `--format relatorio_fat` (ele força vírgula e não usa o cabeçalho).

Use o modo padrão (cabeçalho + separador `;`):

```bash
docker compose exec web python manage.py import_vendas_csv /app/dados/Relatorio_Fat.csv --truncate
```

Ou localmente:

```bash
python manage.py import_vendas_csv dados/Relatorio_Fat.csv --truncate
```

O default do comando já é `--sep ';'` e `--encoding utf-8-sig`; com isso o novo CSV é lido corretamente.
