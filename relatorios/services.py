# -*- coding: utf-8 -*-
"""
Queries de agregação para dashboard e relatório, aplicando UserScope e permissões.
"""
from datetime import time as dt_time
from decimal import Decimal
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone

from .models import StgVendas, UserScope
from django.conf import settings


def get_queryset_vendas(user, data_inicio=None, data_fim=None, codfilial=None, supervisor=None, secao=None, categoria=None,
                        cliente=None, vendedor=None, fornecedor=None, produto=None, filter_fornecedor_as_secao=False, q=None):
    """
    Retorna queryset de StgVendas filtrado por parâmetros e pelo escopo do usuário.
    - Se não tem permissão "pode_ver_todas_filiais", aplica filiais_permitidas do UserScope.
    - Se UserScope tem supervisores_permitidos, filtra por eles.
    """
    from datetime import datetime as dt_type
    perm_todas = 'relatorios.pode_ver_todas_filiais'
    qs = StgVendas.objects.all()

    # Filtro por data: usar intervalo datetime (mais confiável que __date__ no SQLite)
    if data_inicio is not None or data_fim is not None:
        if data_inicio is not None and data_fim is not None:
            start = dt_type.combine(data_inicio, dt_time.min)
            end = dt_type.combine(data_fim, dt_time.max)
            if timezone.is_naive(start):
                start = timezone.make_aware(start)
            if timezone.is_naive(end):
                end = timezone.make_aware(end)
            qs = qs.filter(data_faturamento__gte=start, data_faturamento__lte=end)
        elif data_inicio is not None:
            start = dt_type.combine(data_inicio, dt_time.min)
            if timezone.is_naive(start):
                start = timezone.make_aware(start)
            qs = qs.filter(data_faturamento__gte=start)
        else:
            end = dt_type.combine(data_fim, dt_time.max)
            if timezone.is_naive(end):
                end = timezone.make_aware(end)
            qs = qs.filter(data_faturamento__lte=end)
    if codfilial:
        qs = qs.filter(codfilial=codfilial)
    if supervisor:
        qs = qs.filter(supervisor=supervisor)
    if secao:
        qs = qs.filter(secao=secao)
    if categoria:
        qs = qs.filter(categoria=categoria)
    if cliente:
        qs = qs.filter(cliente=cliente)
    if vendedor:
        qs = qs.filter(nomerca=vendedor)
    if fornecedor:
        # Quando o dropdown é preenchido com seção (fallback), filtrar por seção
        if filter_fornecedor_as_secao:
            qs = qs.filter(secao=fornecedor)
        else:
            qs = qs.filter(fornecedor=fornecedor)
    if produto:
        qs = qs.filter(produto=produto)
    # Pesquisa livre (nota, cliente, produto, supervisor, vendedor, etc.)
    if q and q.strip():
        termo = q.strip()
        qs = qs.filter(
            Q(numnota__icontains=termo) |
            Q(cliente__icontains=termo) |
            Q(produto__icontains=termo) |
            Q(supervisor__icontains=termo) |
            Q(nomerca__icontains=termo) |
            Q(fornecedor__icontains=termo) |
            Q(secao__icontains=termo) |
            Q(codfilial__icontains=termo)
        )

    # Escopo do usuário (não-admin)
    if user.is_authenticated and not user.is_superuser:
        try:
            scope = user.scope
        except UserScope.DoesNotExist:
            scope = None
        if scope:
            if scope.filiais_permitidas:
                qs = qs.filter(codfilial__in=scope.filiais_permitidas)
            elif not user.has_perm(perm_todas):
                # Sem permissão "todas filiais" e sem filiais listadas = não mostra nada (ou ajuste sua regra)
                qs = qs.none()
            if scope.supervisores_permitidos:
                qs = qs.filter(supervisor__in=scope.supervisores_permitidos)
        elif not user.has_perm(perm_todas):
            qs = qs.none()

    return qs


def get_cards_kpis(qs):
    """Retorna dict com totais para cards: total_vendido, qtd_itens, peso_total, devolucao, bonificacao, ticket_medio."""
    agg = qs.aggregate(
        total=Sum('valortotal'),
        qtd=Sum('qtd'),
        peso=Sum('peso'),
        devolucao=Sum('vldevolucao'),
        bonificacao=Sum('valorbonificado'),
        num_notas=Count('numnota', distinct=True),
    )
    total = agg['total'] or Decimal('0')
    num_notas = agg['num_notas'] or 0
    ticket = (total / num_notas) if num_notas else Decimal('0')
    return {
        'total_vendido': total,
        'qtd_itens': agg['qtd'] or Decimal('0'),
        'peso_total': agg['peso'] or Decimal('0'),
        'devolucao': agg['devolucao'] or Decimal('0'),
        'bonificacao': agg['bonificacao'] or Decimal('0'),
        'ticket_medio': ticket,
        'num_notas': num_notas,
    }


def get_serie_temporal(qs, agrupamento='dia'):
    """Série temporal: por dia ou por mês. Retorna lista de {periodo, valor}."""
    if agrupamento == 'mes':
        qs = qs.annotate(periodo=TruncMonth('data_faturamento'))
    else:
        qs = qs.annotate(periodo=TruncDate('data_faturamento'))
    return [
        {'periodo': str(p), 'valor': float(v) if v else 0}
        for p, v in qs.values('periodo').annotate(valor=Sum('valortotal')).order_by('periodo').values_list('periodo', 'valor')
        if p is not None
    ]


def get_top_produtos(qs, limit=10):
    """Top N produtos por valor."""
    return list(
        qs.values('produto')
        .annotate(valor=Sum('valortotal'), qtd=Sum('qtd'))
        .order_by('-valor')[:limit]
    )


def get_vendas_por_filial(qs):
    """Vendas agregadas por filial."""
    return list(qs.values('codfilial').annotate(valor=Sum('valortotal')).order_by('-valor'))


def get_vendas_por_supervisor(qs, limit=15):
    """Vendas agregadas por supervisor."""
    return list(
        qs.values('supervisor')
        .annotate(valor=Sum('valortotal'))
        .order_by('-valor')[:limit]
    )


def get_top_clientes(qs, limit=50):
    """Top N clientes por valor (para gráfico com barra de rolagem)."""
    return list(
        qs.values('cliente')
        .annotate(valor=Sum('valortotal'))
        .order_by('-valor')[:limit]
    )


def get_top_fornecedores(qs, limit=50):
    """Top N fornecedores por valor (para gráfico com barra de rolagem)."""
    return list(
        qs.values('fornecedor')
        .annotate(valor=Sum('valortotal'))
        .order_by('-valor')
        .exclude(fornecedor='')[:limit]
    )


def get_top_secoes(qs, limit=50):
    """Top N seções por valor (usado como fallback quando fornecedor está vazio)."""
    return list(
        qs.values('secao')
        .annotate(valor=Sum('valortotal'))
        .order_by('-valor')
        .exclude(secao='')[:limit]
    )


def get_top_vendedores(qs, limit=50):
    """Top N vendedores (nomerca) por valor (para gráfico com barra de rolagem)."""
    return list(
        qs.values('nomerca')
        .annotate(valor=Sum('valortotal'))
        .order_by('-valor')
        .exclude(nomerca='')[:limit]
    )


def get_mix_secao_categoria(qs, limit=10):
    """Mix por seção ou categoria (valor)."""
    return list(
        qs.values('secao', 'categoria')
        .annotate(valor=Sum('valortotal'))
        .order_by('-valor')[:limit]
    )
