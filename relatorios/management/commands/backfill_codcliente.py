# -*- coding: utf-8 -*-
"""
Preenche codcliente na tabela stg_vendas a partir dos CSV (Relatorio_Fat_*.csv).
Use quando os registros foram importados sem o código do cliente (ex.: import antigo ou separador errado).

Comando: python manage.py backfill_codcliente [dados/] [--sep ;] [--pattern Relatorio_Fat_*.csv]
"""
import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from relatorios.models import StgVendas

# Índices do CSV (mesmo do import_vendas_csv): CODCLI=4, CLIENTE=5
IDX_CODCLI = 4
IDX_CLIENTE = 5
MIN_COLS = 6


def _collect_csv_paths(path, pattern):
    p = Path(path)
    if not p.exists():
        return []
    if p.is_file():
        return [p]
    return sorted([f for f in p.glob(pattern) if f.is_file()])


class Command(BaseCommand):
    help = 'Preenche codcliente a partir dos CSV (Relatorio_Fat_*.csv).'

    def add_arguments(self, parser):
        parser.add_argument(
            'caminho',
            nargs='?',
            type=str,
            default='dados',
            help='Pasta ou ficheiro CSV (default: dados)',
        )
        parser.add_argument('--sep', type=str, default=';', help='Separador CSV (default: ;)')
        parser.add_argument('--pattern', type=str, default='Relatorio_Fat_*.csv', help='Glob na pasta')
        parser.add_argument('--dry-run', action='store_true', help='Apenas mostrar o que seria atualizado')

    def handle(self, *args, **options):
        path = Path(options['caminho'])
        pattern = options.get('pattern') or 'Relatorio_Fat_*.csv'
        sep = options['sep']
        dry_run = options.get('dry_run', False)

        if not path.exists():
            self.stderr.write(self.style.ERROR(f'Caminho não encontrado: {path}'))
            return

        paths = _collect_csv_paths(path, pattern)
        if not paths:
            self.stderr.write(self.style.WARNING(f'Nenhum ficheiro em {path} com padrão "{pattern}".'))
            return

        # Coletar (codcli, cliente) dos CSV
        pares = set()
        for fp in paths:
            for enc in ('utf-8', 'utf-8-sig', 'latin-1', 'cp1252'):
                try:
                    with open(fp, 'r', encoding=enc, newline='') as f:
                        reader = csv.reader(f, delimiter=sep, quoting=csv.QUOTE_NONE)
                        for i, row in enumerate(reader):
                            if i == 0 or not row or len(row) < MIN_COLS:
                                continue
                            cod = (row[IDX_CODCLI] or '').strip()
                            nome = (row[IDX_CLIENTE] or '').strip()
                            if cod and nome:
                                pares.add((cod, nome))
                    break
                except (UnicodeDecodeError, Exception):
                    continue

        if not pares:
            self.stdout.write(self.style.WARNING('Nenhum par CODCLI/CLIENTE encontrado nos CSV.'))
            return

        self.stdout.write(f'Encontrados {len(pares)} pares (CodCli, Cliente) nos CSV.')

        if dry_run:
            for cod, nome in sorted(pares, key=lambda x: (x[1], x[0]))[:20]:
                self.stdout.write(f'  {cod} | {nome}')
            if len(pares) > 20:
                self.stdout.write(f'  ... e mais {len(pares) - 20}.')
            self.stdout.write(self.style.SUCCESS('Dry-run. Nada foi alterado.'))
            return

        updated_total = 0
        with transaction.atomic():
            for cod, cliente in pares:
                n = StgVendas.objects.filter(cliente=cliente, codcliente='').update(codcliente=cod)
                if n > 0:
                    updated_total += n

        self.stdout.write(self.style.SUCCESS(f'Atualizados {updated_total} registros com codcliente.'))
