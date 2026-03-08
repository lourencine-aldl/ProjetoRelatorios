# -*- coding: utf-8 -*-
"""Testes do app relatorios: utils_parse, services, views, comando de import."""
from decimal import Decimal
from datetime import datetime

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from .models import StgVendas, UserScope
from .utils_parse import parse_decimal_br, parse_date_br, parse_codigo
from .services import (
    get_queryset_vendas,
    get_cards_kpis,
    get_serie_temporal,
    get_top_produtos,
    get_vendas_por_filial,
    get_vendas_por_supervisor,
)
from .management.commands.import_vendas_csv import row_from_relatorio_fat, row_to_stg, RELATORIO_FAT_MAP


class TestUtilsParse(TestCase):
    """Testes de normalização pt-BR (utils_parse)."""

    def test_parse_decimal_br_virgula(self):
        self.assertEqual(parse_decimal_br('3,14'), Decimal('3.14'))
        self.assertEqual(parse_decimal_br('98,32'), Decimal('98.32'))

    def test_parse_decimal_br_7459_944(self):
        """7.459.944 (só pontos) e 7.459,944 (vírgula decimal) = 7459,944 (não 7 milhões)."""
        self.assertEqual(parse_decimal_br('7.459.944'), Decimal('7459.944'))
        self.assertEqual(parse_decimal_br('7.459,944'), Decimal('7459.944'))

    def test_parse_decimal_br_vazio(self):
        self.assertIsNone(parse_decimal_br(''))
        self.assertIsNone(parse_decimal_br(None))

    def test_parse_date_br_pt(self):
        dt = parse_date_br('01-fev-2024')
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2024)
        self.assertEqual(dt.month, 2)
        self.assertEqual(dt.day, 1)

    def test_parse_date_br_iso(self):
        dt = parse_date_br('2024-06-15')
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2024)
        self.assertEqual(dt.month, 6)
        self.assertEqual(dt.day, 15)

    def test_parse_codigo_cientifico(self):
        # Mantém como string; evita 1.72E+09 virar científico
        s = parse_codigo('1720040597')
        self.assertEqual(s, '1720040597')

    def test_parse_codigo_vazio(self):
        self.assertEqual(parse_codigo(''), '')
        self.assertEqual(parse_codigo(None), '')


class TestServices(TestCase):
    """Testes dos services (agregações e escopo)."""

    def setUp(self):
        self.user_super = User.objects.create_user('super', password='senha')
        self.user_super.is_superuser = True
        self.user_super.save()

        self.user_scope = User.objects.create_user('scope', password='senha')
        ct = ContentType.objects.get_for_model(StgVendas)
        perm = Permission.objects.get(codename='pode_ver_todas_filiais')
        self.user_scope.user_permissions.add(perm)

        self.dt = timezone.make_aware(datetime(2024, 3, 15, 10, 0))
        StgVendas.objects.create(
            numnota='N001', numped='P001', valortotal=Decimal('100'), valor_liquido=Decimal('100'), qtd=Decimal('2'),
            data_faturamento=self.dt, codfilial='01', supervisor='João', cliente='Cliente A', produto='Prod X',
        )
        StgVendas.objects.create(
            numnota='N002', numped='P002', valortotal=Decimal('200'), valor_liquido=Decimal('200'), qtd=Decimal('1'),
            data_faturamento=self.dt, codfilial='02', supervisor='Maria', cliente='Cliente B', produto='Prod Y',
        )
        StgVendas.objects.create(
            numnota='N003', numped='P003', valortotal=Decimal('50'), valor_liquido=Decimal('50'), qtd=Decimal('3'),
            data_faturamento=self.dt, codfilial='01', supervisor='João', cliente='Cliente C', produto='Prod X',
        )

    def test_get_queryset_vendas_superuser_ve_tudo(self):
        qs = get_queryset_vendas(self.user_super)
        self.assertEqual(qs.count(), 3)

    def test_get_queryset_vendas_filtro_filial(self):
        qs = get_queryset_vendas(self.user_super, codfilial='01')
        self.assertEqual(qs.count(), 2)
        self.assertTrue(qs.filter(codfilial='01').exists())

    def test_get_queryset_vendas_user_scope_filiais(self):
        UserScope.objects.create(user=self.user_scope, filiais_permitidas=['01'])
        qs = get_queryset_vendas(self.user_scope)
        self.assertEqual(qs.count(), 2)  # só filial 01
        self.assertTrue(all(v.codfilial == '01' for v in qs))

    def test_get_cards_kpis(self):
        qs = StgVendas.objects.all()
        cards = get_cards_kpis(qs)
        self.assertEqual(cards['total_vendido'], Decimal('350'))
        self.assertEqual(cards['qtd_itens'], Decimal('6'))
        self.assertEqual(cards['num_notas'], 3)
        self.assertGreater(cards['ticket_medio'], 0)

    def test_get_serie_temporal(self):
        qs = StgVendas.objects.all()
        serie = get_serie_temporal(qs, 'dia')
        self.assertEqual(len(serie), 1)
        self.assertEqual(serie[0]['valor'], 350.0)

    def test_get_top_produtos(self):
        qs = StgVendas.objects.all()
        top = get_top_produtos(qs, 5)
        self.assertEqual(len(top), 2)  # Prod X e Prod Y
        self.assertEqual(top[0]['produto'], 'Prod Y')  # 200 > 150
        self.assertEqual(float(top[0]['valor']), 200.0)

    def test_get_vendas_por_filial(self):
        qs = StgVendas.objects.all()
        por_filial = get_vendas_por_filial(qs)
        self.assertEqual(len(por_filial), 2)
        filiais_valor = {f['codfilial']: float(f['valor']) for f in por_filial}
        self.assertEqual(filiais_valor['01'], 150.0)
        self.assertEqual(filiais_valor['02'], 200.0)


class TestViews(TestCase):
    """Testes de views (login, dashboard, export)."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('teste', password='senha')
        ct = ContentType.objects.get_for_model(StgVendas)
        self.perm_vendas = Permission.objects.get(codename='pode_ver_relatorio_vendas')
        self.perm_excel = Permission.objects.get(codename='pode_exportar_excel')
        self.user.user_permissions.add(self.perm_vendas, self.perm_excel)

    def test_login_redirect_se_nao_autenticado(self):
        r = self.client.get(reverse('dashboard'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('login', r.url)

    def test_dashboard_requer_permissao(self):
        user_sem_perm = User.objects.create_user('noperm', password='senha')
        self.client.force_login(user_sem_perm)
        r = self.client.get(reverse('dashboard'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'permissão')  # template sem_permissao

    def test_dashboard_ok_com_permissao(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse('dashboard'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Dashboard de Vendas')

    def test_export_excel_403_sem_permissao(self):
        user_sem_perm = User.objects.create_user('noperm2', password='senha')
        self.client.force_login(user_sem_perm)
        r = self.client.get(reverse('export_excel'))
        self.assertEqual(r.status_code, 403)

    def test_export_excel_200_com_permissao(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse('export_excel'))
        self.assertEqual(r.status_code, 200)
        self.assertIn('spreadsheet', r.get('Content-Type', ''))


class TestImportCommand(TestCase):
    """Testes do comando import_vendas_csv (row_from_relatorio_fat, row_to_stg)."""

    def test_row_from_relatorio_fat(self):
        # Índices do RELATORIO_FAT_MAP: codfilial=0, data=1, cliente=5, produto=12, qtd=15,
        # valortotal=19, supervisor=24, nomerca=26, secao=28, categoria=37, numnota=45, numped=46
        cols = [''] * 60
        cols[0] = '02'
        cols[1] = '01-fev-2024'
        cols[5] = 'Cliente Teste'
        cols[12] = 'Produto X'
        cols[15] = '2'
        cols[17] = '1,5'
        cols[19] = '99,90'
        cols[24] = 'Supervisor A'
        cols[26] = 'RCA Nome'
        cols[28] = 'Seção'
        cols[37] = 'Categoria'
        cols[45] = '1284874'
        cols[46] = '1720040597'
        row = row_from_relatorio_fat(cols)
        self.assertEqual(row['DATA_FATURAMENTO'], '01-fev-2024')
        self.assertEqual(row['CODFILIAL'], '02')
        self.assertEqual(row['CLIENTE'], 'Cliente Teste')
        self.assertEqual(row['PRODUTO'], 'Produto X')
        self.assertEqual(row['VALORTOTAL'], '99,90')
        self.assertEqual(row['NUMNOTA'], '1284874')
        self.assertEqual(row['NUMPED'], '1720040597')

    def test_row_to_stg_com_dict(self):
        row = {
            'DATA_FATURAMENTO': '01-fev-2024',
            'CODFILIAL': '01',
            'CLIENTE': 'Cliente',
            'PRODUTO': 'Produto',
            'VALORTOTAL': '100,50',
            'QTD': '3',
            'NUMNOTA': 'N001',
            'NUMPED': 'P001',
            'SUPERVISOR': 'João',
        }
        stg = row_to_stg(row)
        self.assertEqual(stg.numnota, 'N001')
        self.assertEqual(stg.codfilial, '01')
        self.assertEqual(stg.valortotal, Decimal('100.50'))
        self.assertEqual(stg.qtd, Decimal('3'))
        self.assertIsNotNone(stg.data_faturamento)
        self.assertEqual(stg.data_faturamento.day, 1)
        self.assertEqual(stg.data_faturamento.month, 2)
        self.assertEqual(stg.data_faturamento.year, 2024)
