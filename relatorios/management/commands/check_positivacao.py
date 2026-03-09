# -*- coding: utf-8 -*-
"""
Diagnóstico: por que a Positivação está zerada?
Comando: python manage.py check_positivacao
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db.models import Q, Count
from django.utils import timezone

from relatorios.models import StgVendas


class Command(BaseCommand):
    help = 'Verifica por que a Positivação pode estar zerada (codcliente, qtdevol, dados no período).'

    def handle(self, *args, **options):
        total = StgVendas.objects.count()
        self.stdout.write(f'Total de registros em stg_vendas: {total}')

        if total == 0:
            self.stdout.write(self.style.WARNING('Base vazia. Execute: python manage.py import_vendas_csv dados/'))
            return

        com_codcliente = StgVendas.objects.exclude(codcliente='').filter(codcliente__isnull=False).count()
        qtdevol_zero = StgVendas.objects.filter(qtdevol=0).count()
        qtdevol_null = StgVendas.objects.filter(qtdevol__isnull=True).count()
        qtdevol_ok = StgVendas.objects.filter(Q(qtdevol=0) | Q(qtdevol__isnull=True)).count()

        self.stdout.write(f'Registros com codcliente preenchido: {com_codcliente}')
        self.stdout.write(f'Registros com qtdevol = 0: {qtdevol_zero}')
        self.stdout.write(f'Registros com qtdevol NULL: {qtdevol_null}')
        self.stdout.write(f'Registros com qtdevol = 0 ou NULL: {qtdevol_ok}')

        # Positivação: período ano anterior até este ano (compatível com SQLite)
        from datetime import date
        hoje = timezone.now().date()
        ano_inicio = hoje.year - 1
        qs = StgVendas.objects.filter(
            data_faturamento__year__gte=ano_inicio,
            data_faturamento__year__lte=hoje.year,
        )
        no_periodo = qs.count()
        self.stdout.write(f'Registros no período (ano anterior até hoje): {no_periodo}')

        positividade = (
            qs.filter(codcliente__isnull=False)
            .exclude(codcliente='')
            .filter(Q(qtdevol=0) | Q(qtdevol__isnull=True))
            .values('codcliente', 'data_faturamento__year', 'data_faturamento__month')
            .distinct()
            .count()
        )
        self.stdout.write(f'Positivação (distinct codcliente+mês, QTDEVOL=0/NULL) no período: {positividade}')

        if com_codcliente == 0:
            self.stdout.write(self.style.ERROR(
                'Nenhum registro tem codcliente preenchido. '
                'Reimporte os CSV sem --format: python manage.py import_vendas_csv dados/ --truncate'
            ))
        elif positividade == 0 and no_periodo > 0:
            self.stdout.write(self.style.WARNING(
                'Há dados no período e codcliente preenchido, mas Positivação=0. '
                'Verifique se qtdevol está 0 ou NULL nos registros do período.'
            ))
