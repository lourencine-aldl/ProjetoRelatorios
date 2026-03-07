# -*- coding: utf-8 -*-
"""
Comando: python manage.py import_vendas_csv <caminho_csv> [--truncate] [--sep SEP] [--encoding ENC] [--format FORMAT]
Normaliza pt-BR (vírgula, datas, códigos como string) e faz bulk_create em StgVendas.
--format relatorio_fat: CSV sem cabeçalho, separador vírgula, mapeamento fixo por coluna (relatorio_fat.csv).
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
# CSV com cabeçalho na 1ª linha, vírgula, campos entre aspas (usar QUOTE_NONE para split correto)
# Ordem real: CODFILIAL=0, DATA_FATURAMENTO=1, CLIENTE=5, PRODUTO=12, QTD=15, PESO=17, VALORTOTAL=19,
# FORNECEDOR=22, SUPERVISOR=24, NOMERCA=26, SECAO=28, VALORBONIFICADO=34, VLDEVOLUCAO=35, CATEGORIA=37,
# SUBCATEGORIA=39, VALOR_LIQUIDO=40, NUMNOTA=45, NUMPED=46
RELATORIO_FAT_MAP = {
    'codfilial': 0, 'data': 1, 'cliente': 5, 'produto': 12, 'qtd': 15, 'peso': 17,
    'valortotal': 19, 'fornecedor': 22, 'supervisor': 24, 'nomerca': 26, 'secao': 28,
    'valorbonificado': 34, 'vldevolucao': 35, 'categoria': 37, 'subcategoria': 39,
    'valor_liquido': 40, 'numnota': 45, 'numped': 46,
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


def row_to_stg(row, encoding='utf-8-sig'):
    """Converte um dict de linha CSV (chaves podem variar) para StgVendas."""
    def _key_variants(key):
        return [key, key.upper(), key.lower(), key.replace('_', ' ')]

    def g(key, default=''):
        for k in _key_variants(key):
            v = row.get(k)
            if v is not None and str(v).strip() != '':
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
        cliente=g('CLIENTE'),
    )


class Command(BaseCommand):
    help = 'Importa CSV de vendas para stg_vendas com normalização pt-BR'

    def add_arguments(self, parser):
        parser.add_argument('caminho_csv', type=str, help='Caminho do arquivo CSV')
        parser.add_argument('--truncate', action='store_true', help='Apagar registros existentes antes de importar')
        parser.add_argument('--sep', type=str, default=';', help='Separador CSV (default: ;)')
        parser.add_argument('--encoding', type=str, default='utf-8-sig', help='Encoding do arquivo (default: utf-8-sig)')
        parser.add_argument('--batch', type=int, default=5000, help='Tamanho do batch para bulk_create')
        parser.add_argument('--format', type=str, default='', help='Formato: vazio (com cabeçalho) ou relatorio_fat (sem cabeçalho, vírgula)')

    def handle(self, *args, **options):
        path = Path(options['caminho_csv'])
        if not path.exists():
            self.stderr.write(self.style.ERROR(f'Arquivo não encontrado: {path}'))
            return

        fmt = (options.get('format') or '').strip().lower()
        truncate = options['truncate']
        batch_size = options['batch']

        if fmt == 'relatorio_fat':
            sep = ','
            # CSV com cabeçalho na 1ª linha; linhas entre aspas = 1 coluna. Usar QUOTE_NONE para obter colunas corretas.
            min_cols = max(RELATORIO_FAT_MAP.values()) + 1
            for encoding in ('utf-8', 'utf-8-sig', 'latin-1', 'cp1252'):
                try:
                    with open(path, 'r', encoding=encoding, newline='') as f:
                        reader = csv.reader(f, delimiter=sep, quoting=csv.QUOTE_NONE)
                        all_rows = list(reader)
                    if not all_rows:
                        rows = []
                        break
                    # Primeira linha: cabeçalho (pode ser 1 coluna se toda a linha estiver entre aspas)
                    first = all_rows[0]
                    if len(first) < min_cols:
                        # Linhas estão “quoted” (1 coluna por linha): descartar e manter rows vazio
                        rows = []
                        self.stderr.write(self.style.WARNING(
                            f'CSV com 1 coluna por linha (aspas). Use formato com colunas separadas por vírgula.'
                        ))
                    else:
                        # Pular cabeçalho; exigir pelo menos min_cols colunas por linha
                        rows = [row_from_relatorio_fat(row) for row in all_rows[1:] if row and len(row) >= min_cols]
                    break
                except UnicodeDecodeError:
                    continue
            else:
                self.stderr.write(self.style.ERROR('Encoding do arquivo não reconhecido. Tente --encoding latin-1 ou cp1252.'))
                return
        else:
            sep = options['sep']
            encoding = options['encoding']
            with open(path, 'r', encoding=encoding, newline='') as f:
                reader = csv.DictReader(f, delimiter=sep)
                rows = list(reader)

        if not rows:
            self.stdout.write('CSV vazio.')
            return

        with transaction.atomic():
            if truncate:
                deleted, _ = StgVendas.objects.all().delete()
                self.stdout.write(f'Removidos {deleted} registros.')

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
                    except Exception as e:
                        for obj in batch:
                            try:
                                obj.save()
                                created += 1
                            except Exception:
                                pass
                        self.stderr.write(f'Batch com erro (inseridos 1 a 1): {e}')
                    batch = []
                    self.stdout.write(f'Inseridos {created}...')

            if batch:
                try:
                    StgVendas.objects.bulk_create(batch)
                    created += len(batch)
                except Exception as e:
                    for obj in batch:
                        try:
                            obj.save()
                            created += 1
                        except Exception:
                            pass
                    self.stderr.write(f'Último batch com erro: {e}')

        self.stdout.write(self.style.SUCCESS(f'Importação concluída: {created} registros.'))
