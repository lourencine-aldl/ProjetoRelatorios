# -*- coding: utf-8 -*-
"""
Comando: python manage.py import_vendas_csv <caminho> [--truncate] [--sep SEP] [--encoding ENC] [--format FORMAT] [--pattern GLOB]

<caminho> pode ser:
  - Um arquivo CSV (importa só esse arquivo).
  - Uma pasta (ex.: dados/): importa todos os CSV da pasta que batem com --pattern (padrão: Relatorio_Fat_*.csv).
  Mesmo padrão de colunas em todos; use por período para reduzir carga (vários arquivos na pasta).
"""
import csv
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone as tz

from relatorios.models import StgVendas
from relatorios.utils_parse import parse_decimal_br, parse_date_br, parse_codigo, safe_decimal_for_db


# Mapeamento por índice (0-based) para formato relatorio_fat
# CSV separado por ; (semicolon), 1ª linha = cabeçalho (ex.: Relatorio_Fat_2025.csv, Relatorio_Fat_2026.csv)
# Ordem: CODFILIAL=0, DATA_FATURAMENTO=1, MES=2, ANO=3, CODCLI=4, CLIENTE=5, ..., PRODUTO=12, QTD=15, ...
RELATORIO_FAT_MAP = {
    'codfilial': 0, 'data': 1, 'codcli': 4, 'cliente': 5, 'produto': 12, 'qtd': 15, 'peso': 17,
    'valortotal': 19, 'fornecedor': 22, 'supervisor': 24, 'nomerca': 26, 'secao': 28,
    'valorbonificado': 34, 'vldevolucao': 35, 'categoria': 37, 'subcategoria': 39,
    'valor_liquido': 40, 'numnota': 45, 'numped': 46,
}

# Formato Fat: 1ª coluna = CLIENTE_FORMATADO, depois CODFILIAL, DATA, MES, ANO, CODCLI=5, CLIENTE=6, ...
# (Fat_2025.1, fat_2026.1, etc.)
FAT_FORMAT_MAP = {
    'cliente_formatado': 0, 'codfilial': 1, 'data': 2, 'mes': 3, 'ano': 4, 'codcli': 5, 'cliente': 6,
    'produto': 14, 'qtd': 17, 'peso': 19, 'pesoliq': 20, 'valortotal': 21, 'ptabela': 22,
    'fornecedor': 24, 'supervisor': 26, 'nomerca': 28, 'secao': 30, 'categoria': 39, 'subcategoria': 41,
    'valorbonificado': 36, 'vldevolucao': 37, 'valor_liquido': 42, 'numnota': 47, 'numped': 48,
    'qtdevol': 18,
}

def _strip_quotes(s):
    """Remove aspas duplas que envolvem ou iniciam campos no CSV (QUOTE_NONE deixa aspas no valor)."""
    if s is None:
        return ''
    s = str(s).strip()
    if len(s) >= 2 and s.startswith('"') and s.endswith('"'):
        s = s[1:-1].replace('""', '"')
    elif s.startswith('"'):
        s = s[1:]
    elif s.endswith('"'):
        s = s[:-1]
    return s


def row_from_relatorio_fat(cols):
    """Converte lista de colunas (relatorio_fat) para dict compatível com row_to_stg."""
    def v(idx, default=''):
        if idx is None or idx >= len(cols):
            return default
        return _strip_quotes(cols[idx]) or default
    return {
        'DATA_FATURAMENTO': v(RELATORIO_FAT_MAP['data']),
        'CODFILIAL': v(RELATORIO_FAT_MAP['codfilial']),
        'CODCLI': v(RELATORIO_FAT_MAP.get('codcli')),
        'CLIENTE': v(RELATORIO_FAT_MAP['cliente']),
        'PRODUTO': v(RELATORIO_FAT_MAP['produto']),
        'QTD': v(RELATORIO_FAT_MAP['qtd']),
        'PESO': v(RELATORIO_FAT_MAP['peso']),
        'VALORTOTAL': v(RELATORIO_FAT_MAP['valortotal']),
        'SUPERVISOR': v(RELATORIO_FAT_MAP['supervisor']),
        'NOMERCA': v(RELATORIO_FAT_MAP['nomerca']),
        'SECAO': v(RELATORIO_FAT_MAP['secao']),
        'CATEGORIA': v(RELATORIO_FAT_MAP['categoria']),
        'SUBCATEGORIA': v(RELATORIO_FAT_MAP.get('subcategoria')),
        'NUMNOTA': v(RELATORIO_FAT_MAP['numnota']),
        'NUMPED': v(RELATORIO_FAT_MAP['numped']),
        'VALOR_LIQUIDO': v(RELATORIO_FAT_MAP.get('valor_liquido')),
        'VLDEVOLUCAO': v(RELATORIO_FAT_MAP.get('vldevolucao')),
        'VALORBONIFICADO': v(RELATORIO_FAT_MAP.get('valorbonificado')),
        'FORNECEDOR': v(RELATORIO_FAT_MAP.get('fornecedor')),
    }


def row_from_fat(cols):
    """Converte lista de colunas (formato Fat: CLIENTE_FORMATADO na col 0, CODCLI na col 5) para dict."""
    def v(idx, default=''):
        if idx is None or idx >= len(cols):
            return default
        return _strip_quotes(cols[idx]) or default
    return {
        'DATA_FATURAMENTO': v(FAT_FORMAT_MAP['data']),
        'CODFILIAL': v(FAT_FORMAT_MAP['codfilial']),
        'CODCLI': v(FAT_FORMAT_MAP['codcli']),
        'CLIENTE': v(FAT_FORMAT_MAP['cliente']),
        'CLIENTE_FORMATADO': v(FAT_FORMAT_MAP['cliente_formatado']),
        'PRODUTO': v(FAT_FORMAT_MAP['produto']),
        'QTD': v(FAT_FORMAT_MAP['qtd']),
        'PESO': v(FAT_FORMAT_MAP['peso']),
        'PESOLIQ': v(FAT_FORMAT_MAP.get('pesoliq')),
        'VALORTOTAL': v(FAT_FORMAT_MAP['valortotal']),
        'PTABELA': v(FAT_FORMAT_MAP.get('ptabela')),
        'SUPERVISOR': v(FAT_FORMAT_MAP['supervisor']),
        'NOMERCA': v(FAT_FORMAT_MAP['nomerca']),
        'SECAO': v(FAT_FORMAT_MAP['secao']),
        'CATEGORIA': v(FAT_FORMAT_MAP['categoria']),
        'SUBCATEGORIA': v(FAT_FORMAT_MAP.get('subcategoria')),
        'NUMNOTA': v(FAT_FORMAT_MAP['numnota']),
        'NUMPED': v(FAT_FORMAT_MAP['numped']),
        'VALOR_LIQUIDO': v(FAT_FORMAT_MAP.get('valor_liquido')),
        'VLDEVOLUCAO': v(FAT_FORMAT_MAP.get('vldevolucao')),
        'VALORBONIFICADO': v(FAT_FORMAT_MAP.get('valorbonificado')),
        'FORNECEDOR': v(FAT_FORMAT_MAP.get('fornecedor')),
        'QTDEVOL': v(FAT_FORMAT_MAP.get('qtdevol')),
    }


def row_to_stg(row, encoding='utf-8-sig'):
    """Converte um dict de linha CSV (chaves podem variar) para StgVendas."""
    def _key_variants(key):
        return [key, key.upper(), key.lower(), key.replace('_', ' ')]

    def g(key, default=''):
        for k in _key_variants(key):
            v = row.get(k)
            if v is not None and str(v).strip() != '':
                return str(v).strip()
        # Fallback: procurar chave que bata ignorando maiúsculas (ex.: CSV com "CodCli")
        key_upper = key.upper().replace(' ', '')
        for k, v in row.items():
            if k and str(k).upper().replace(' ', '') == key_upper and v is not None and str(v).strip() != '':
                return str(v).strip()
        return default

    def get_val(key):
        """Retorna o valor bruto tentando várias variantes de chave (CSV pode vir em minúsculo)."""
        for k in _key_variants(key):
            v = row.get(k)
            if v is not None and str(v).strip() != '':
                return v
        return None

    def d(key):
        return parse_decimal_br(get_val(key))

    def sd(val, default=Decimal('0')):
        return safe_decimal_for_db(val, default=default)

    def dt(key):
        return parse_date_br(get_val(key))

    def cod(key):
        return parse_codigo(get_val(key) or g(key))

    return StgVendas(
        numnota=cod('NUMNOTA') or g('numnota'),
        numped=cod('NUMPED') or g('numped'),
        valortotal=sd(d('VALORTOTAL') or d('VALOR TOTAL')),
        valor_liquido=safe_decimal_for_db(d('VALOR_LIQUIDO') or d('VALOR LIQUIDO')),
        qtd=sd(d('QTD')),
        peso=safe_decimal_for_db(d('PESO'), decimal_places=6),
        pesoliq=safe_decimal_for_db(d('PESOLIQ') or d('PESO LIQ'), decimal_places=6),
        qtdevol=safe_decimal_for_db(d('QTDEVOL') or d('QTD DEVOL')),
        vldevolucao=safe_decimal_for_db(d('VLDEVOLUCAO') or d('VALOR DEVOLUCAO')),
        valorbonificado=safe_decimal_for_db(d('VALORBONIFICADO') or d('VALOR BONIFICADO')),
        ptabela=safe_decimal_for_db(d('PTABELA') or d('P TABELA')),
        data_faturamento=dt('DATA_FATURAMENTO') or dt('DATA FATURAMENTO') or dt('DATA'),
        codfilial=g('CODFILIAL') or g('COD FILIAL'),
        supervisor=g('SUPERVISOR'),
        nomerca=g('NOMERCA') or g('NOME RCA'),
        produto=g('PRODUTO'),
        fornecedor=g('FORNECEDOR'),
        secao=g('SECAO') or g('SEÇÃO'),
        categoria=g('CATEGORIA'),
        subcategoria=g('SUBCATEGORIA'),
        codcliente=g('CODCLI') or '',
        cliente=g('CLIENTE'),
        cliente_formatado=g('CLIENTE_FORMATADO') or g('CLIENTE FORMATADO') or '',
    )


def _collect_csv_paths(path, pattern):
    """Se path for pasta, retorna lista de arquivos CSV que batem com pattern, ordenados por nome. Senão, [path]."""
    p = Path(path)
    if not p.exists():
        return []
    if p.is_file():
        return [p]
    files = sorted(p.glob(pattern))
    return [f for f in files if f.is_file()]


def _read_rows_from_file(path, fmt, sep, encoding, min_cols, command_self):
    """Lê e normaliza linhas de um único CSV. Retorna (rows, sep_used)."""
    if fmt == 'relatorio_fat':
        for enc in ('utf-8', 'utf-8-sig', 'latin-1', 'cp1252'):
            try:
                with open(path, 'r', encoding=enc, newline='') as f:
                    reader = csv.reader(f, delimiter=sep, quoting=csv.QUOTE_NONE)
                    all_rows = list(reader)
                if not all_rows:
                    return [], sep
                first = all_rows[0]
                if len(first) < min_cols:
                    command_self.stderr.write(command_self.style.WARNING(
                        f'{path.name}: CSV com poucas colunas. Ignorando.'
                    ))
                    return [], sep
                rows = [row_from_relatorio_fat(row) for row in all_rows[1:] if row and len(row) >= min_cols]
                return rows, sep
            except UnicodeDecodeError:
                continue
        command_self.stderr.write(command_self.style.ERROR(f'{path.name}: Encoding não reconhecido.'))
        return [], sep

    # Formato vazio: detectar se é Fat (CLIENTE_FORMATADO na 1ª coluna) e montar dict pelo cabeçalho
    for enc in (encoding, 'utf-8', 'utf-8-sig', 'latin-1', 'cp1252'):
        try:
            with open(path, 'r', encoding=enc, newline='') as f:
                first_line = f.readline()
                first_cols = first_line.strip().split(sep)
                if first_cols and 'CLIENTE_FORMATADO' in (first_cols[0] or '').upper():
                    # Formato Fat: ler por índice e montar dict pelo cabeçalho (CODCLI na coluna certa)
                    f.seek(0)
                    reader = csv.reader(f, delimiter=sep, quoting=csv.QUOTE_NONE)
                    all_rows = list(reader)
                    if not all_rows or len(all_rows) < 2:
                        return [], sep
                    header = [ (h or '').strip() for h in all_rows[0] ]
                    rows = []
                    for row in all_rows[1:]:
                        if not row or len(row) < 6:
                            continue
                        # Montar dict: header[i] -> row[i] (ignora colunas com cabeçalho vazio)
                        row_dict = {}
                        for i in range(min(len(header), len(row))):
                            if header[i]:
                                row_dict[header[i]] = _strip_quotes(row[i]) if i < len(row) else ''
                        rows.append(row_dict)
                    return rows, sep
        except (UnicodeDecodeError, Exception):
            continue

    # Fallback: DictReader (cabeçalho por nome)
    try:
        with open(path, 'r', encoding=encoding, newline='') as f:
            reader = csv.DictReader(f, delimiter=sep)
            rows = list(reader)
    except Exception as e:
        command_self.stderr.write(command_self.style.ERROR(f'{path.name}: {e}'))
        return [], sep
    return rows, sep


class Command(BaseCommand):
    help = 'Importa CSV de vendas para stg_vendas. Aceita arquivo ou pasta (ex.: dados/) com vários CSV.'

    def add_arguments(self, parser):
        parser.add_argument(
            'caminho',
            type=str,
            help='Arquivo CSV ou pasta (ex.: dados/). Com pasta, importa todos *.csv (Fat_2025.1, fat_2026.1, etc.)',
        )
        parser.add_argument('--truncate', action='store_true', help='Apagar registros antes de importar (só no 1º arquivo)')
        parser.add_argument('--sep', type=str, default=';', help='Separador CSV (default: ;)')
        parser.add_argument('--encoding', type=str, default='utf-8-sig', help='Encoding (default: utf-8-sig)')
        parser.add_argument('--batch', type=int, default=5000, help='Tamanho do batch para bulk_create')
        parser.add_argument('--format', type=str, default='', help='vazio (cabeçalho) ou relatorio_fat')
        parser.add_argument('--pattern', type=str, default='*.csv', help='Glob na pasta (default: *.csv para Fat_2025.1, fat_2026.1, etc.)')

    def handle(self, *args, **options):
        path = Path(options['caminho'])
        if not path.exists():
            self.stderr.write(self.style.ERROR(f'Caminho não encontrado: {path}'))
            return

        pattern = options.get('pattern') or '*.csv'
        paths = _collect_csv_paths(path, pattern)

        if not paths:
            if path.is_dir():
                self.stderr.write(self.style.WARNING(
                    f'Nenhum arquivo em {path} com padrão "{pattern}".'
                ))
            else:
                self.stderr.write(self.style.ERROR('Nenhum arquivo para importar.'))
            return

        if path.is_dir():
            self.stdout.write(f'Importando {len(paths)} arquivo(s) de {path}:')
            for fp in paths:
                self.stdout.write(f'  - {fp.name}')

        fmt = (options.get('format') or '').strip().lower()
        batch_size = options['batch']
        sep_option = options['sep']
        encoding = options['encoding']
        min_cols = max(RELATORIO_FAT_MAP.values()) + 1 if fmt == 'relatorio_fat' else 0
        truncate = options['truncate']
        total_created = 0

        with transaction.atomic():
            for file_idx, single_path in enumerate(paths):
                rows, sep = _read_rows_from_file(
                    single_path, fmt, sep_option, encoding, min_cols, self
                )
                if not rows:
                    self.stdout.write(f'{single_path.name}: sem linhas válidas, pulando.')
                    continue

                if truncate and file_idx == 0:
                    deleted, _ = StgVendas.objects.all().delete()
                    self.stdout.write(self.style.WARNING(f'Removidos {deleted} registros (--truncate).'))

                self.stdout.write(f'{single_path.name}: {len(rows)} linhas...')
                created = 0
                batch = []
                for row in rows:
                    try:
                        obj = row_to_stg(row)
                        if obj.data_faturamento and tz.is_naive(obj.data_faturamento):
                            obj.data_faturamento = tz.make_aware(obj.data_faturamento)
                        batch.append(obj)
                    except Exception as e:
                        self.stderr.write(f'Erro na linha: {e}')
                        continue
                    if len(batch) >= batch_size:
                        try:
                            StgVendas.objects.bulk_create(batch)
                            created += len(batch)
                            total_created += len(batch)
                        except Exception as e:
                            for obj in batch:
                                try:
                                    obj.save()
                                    created += 1
                                    total_created += 1
                                except Exception:
                                    pass
                            self.stderr.write(f'Batch com erro (inseridos 1 a 1): {e}')
                        batch = []
                        if total_created % 20000 == 0 or total_created == created:
                            self.stdout.write(f'  Inseridos {total_created}...')
                if batch:
                    try:
                        StgVendas.objects.bulk_create(batch)
                        created += len(batch)
                        total_created += len(batch)
                    except Exception as e:
                        for obj in batch:
                            try:
                                obj.save()
                                created += 1
                                total_created += 1
                            except Exception:
                                pass
                        self.stderr.write(f'Último batch com erro: {e}')
                self.stdout.write(self.style.SUCCESS(f'  {single_path.name}: {created} registros.'))

        self.stdout.write(self.style.SUCCESS(f'Importação concluída: {total_created} registros no total.'))
