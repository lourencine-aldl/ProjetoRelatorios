# -*- coding: utf-8 -*-
"""APIs REST (DRF) para dashboard e relatório detalhado em JSON."""
from django.db.models import Q
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import StgVendas
from .services import (
    get_queryset_vendas,
    get_cards_kpis,
    get_serie_temporal,
    get_top_produtos,
    get_vendas_por_filial,
    get_vendas_por_supervisor,
    get_mix_secao_categoria,
)


def _parse_dates(request):
    from datetime import datetime, timedelta
    from django.utils import timezone
    hoje = timezone.now().date()
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    if data_inicio:
        try:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        except ValueError:
            data_inicio = hoje - timedelta(days=30)
    else:
        data_inicio = hoje - timedelta(days=30)
    if data_fim:
        try:
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
        except ValueError:
            data_fim = hoje
    else:
        data_fim = hoje
    return data_inicio, data_fim


class DashboardAPIView(APIView):
    """GET: retorna cards, série temporal, top produtos, por filial, por supervisor (JSON)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (request.user.is_superuser or request.user.has_perm('relatorios.pode_ver_relatorio_vendas')):
            return Response({'detail': 'Sem permissão.'}, status=status.HTTP_403_FORBIDDEN)

        data_inicio, data_fim = _parse_dates(request)
        qs = get_queryset_vendas(
            request.user,
            data_inicio=data_inicio,
            data_fim=data_fim,
            codfilial=request.GET.get('codfilial') or None,
            supervisor=request.GET.get('supervisor') or None,
            secao=request.GET.get('secao') or None,
            categoria=request.GET.get('categoria') or None,
        )

        cards = get_cards_kpis(qs)
        # Serializar Decimal para float no JSON
        cards_json = {
            'total_vendido': float(cards['total_vendido']),
            'qtd_itens': float(cards['qtd_itens']),
            'peso_total': float(cards['peso_total']),
            'devolucao': float(cards['devolucao']),
            'bonificacao': float(cards['bonificacao']),
            'ticket_medio': float(cards['ticket_medio']),
            'num_notas': cards['num_notas'],
        }

        agrupamento = request.GET.get('agrupamento', 'dia')
        serie = get_serie_temporal(qs, agrupamento)
        top_produtos = get_top_produtos(qs, 10)
        por_filial = get_vendas_por_filial(qs)
        por_supervisor = get_vendas_por_supervisor(qs, 15)
        mix = get_mix_secao_categoria(qs, 10)

        return Response({
            'cards': cards_json,
            'serie_temporal': serie,
            'top_produtos': [{'produto': p['produto'], 'valor': float(p['valor'] or 0), 'qtd': float(p['qtd'] or 0)} for p in top_produtos],
            'vendas_por_filial': [{'codfilial': f['codfilial'], 'valor': float(f['valor'] or 0)} for f in por_filial],
            'vendas_por_supervisor': [{'supervisor': s['supervisor'], 'valor': float(s['valor'] or 0)} for s in por_supervisor],
            'mix_secao_categoria': [{'secao': m['secao'], 'categoria': m['categoria'], 'valor': float(m['valor'] or 0)} for m in mix],
            'filtros': {'data_inicio': str(data_inicio), 'data_fim': str(data_fim)},
        })
