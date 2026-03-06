# -*- coding: utf-8 -*-
import json
from datetime import timedelta
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.http import HttpResponse
from django.utils import timezone

from .models import StgVendas
from .services import (
    get_queryset_vendas,
    get_cards_kpis,
    get_serie_temporal,
    get_top_produtos,
    get_top_clientes,
    get_top_fornecedores,
    get_top_secoes,
    get_top_vendedores,
    get_vendas_por_filial,
    get_vendas_por_supervisor,
    get_mix_secao_categoria,
)
from .export_excel import export_vendas_excel


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect(request.GET.get('next', 'dashboard'))
    else:
        form = AuthenticationForm()
    return render(request, 'relatorios/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


def root_redirect(request):
    """Redireciona / para login ou dashboard."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


@login_required
def dashboard(request):
    perm = 'relatorios.pode_ver_relatorio_vendas'
    if not (request.user.is_superuser or request.user.has_perm(perm)):
        return render(request, 'relatorios/sem_permissao.html')

    hoje = timezone.now().date()
    # Padrão: mês atual (primeiro dia do mês até hoje)
    from datetime import date
    inicio_mes = date(hoje.year, hoje.month, 1)
    data_fim = request.GET.get('data_fim') or hoje
    data_inicio = request.GET.get('data_inicio') or inicio_mes
    if isinstance(data_inicio, str):
        try:
            from datetime import datetime
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        except ValueError:
            data_inicio = date(hoje.year, hoje.month, 1)
    if isinstance(data_fim, str):
        try:
            from datetime import datetime
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
        except ValueError:
            data_fim = hoje
    codfilial = request.GET.get('codfilial', '').strip() or None
    supervisor = request.GET.get('supervisor', '').strip() or None
    secao = request.GET.get('secao', '').strip() or None
    categoria = request.GET.get('categoria', '').strip() or None
    cliente = request.GET.get('cliente', '').strip() or None
    vendedor = request.GET.get('vendedor', '').strip() or None
    fornecedor = request.GET.get('fornecedor', '').strip() or None
    produto = request.GET.get('produto', '').strip() or None
    q = request.GET.get('q', '').strip() or None

    # Verificar se há dados de fornecedor no período (senão usamos seção no filtro e no gráfico)
    qs_escopo = get_queryset_vendas(request.user, data_inicio=data_inicio, data_fim=data_fim)
    try:
        filter_fornecedor_as_secao = not qs_escopo.filter(fornecedor__isnull=False).exclude(fornecedor='').exists()
    except Exception:
        filter_fornecedor_as_secao = True

    qs = get_queryset_vendas(
        request.user,
        data_inicio=data_inicio,
        data_fim=data_fim,
        codfilial=codfilial,
        supervisor=supervisor,
        secao=secao,
        categoria=categoria,
        cliente=cliente,
        vendedor=vendedor,
        fornecedor=fornecedor,
        produto=produto,
        filter_fornecedor_as_secao=filter_fornecedor_as_secao,
        q=q,
    )

    cards = get_cards_kpis(qs)
    agrupamento = request.GET.get('agrupamento', 'dia')
    serie = get_serie_temporal(qs, agrupamento)
    # Labels no eixo X: por mês = MM/AA, por dia = 01/jan/26
    meses_abrev = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
    for item in serie:
        p = item.get('periodo') or ''
        try:
            from datetime import datetime
            s = str(p)[:10]
            if len(s) >= 10:
                dt = datetime.strptime(s, '%Y-%m-%d')
                if agrupamento == 'mes':
                    item['label'] = dt.strftime('%m') + '/' + dt.strftime('%y')  # MM/AA
                else:
                    item['label'] = dt.strftime('%d') + '/' + meses_abrev[dt.month - 1] + '/' + dt.strftime('%y')
            else:
                item['label'] = s
        except Exception:
            item['label'] = p[:10] if len(p) >= 10 else str(p)
    # Top 50 para gráficos com barra de rolagem (mostra top 10 visíveis, scroll para mais)
    top_clientes = get_top_clientes(qs, 50)
    try:
        top_fornecedores = get_top_fornecedores(qs, 50)
    except Exception:
        top_fornecedores = []
    # Se não há fornecedores preenchidos no CSV, usa seção como fallback no gráfico e no filtro
    fornecedores_label = 'Top 10 fornecedores (rolar para ver mais)'
    if filter_fornecedor_as_secao:
        top_secoes = get_top_secoes(qs, 50)
        top_fornecedores = [{'fornecedor': s.get('secao') or '(sem seção)', 'valor': s.get('valor')} for s in top_secoes]
        fornecedores_label = 'Top 10 fornecedores / seção (rolar para ver mais)'
    top_produtos = get_top_produtos(qs, 50)
    por_supervisor = get_vendas_por_supervisor(qs, 50)
    top_vendedores = get_top_vendedores(qs, 50)
    por_filial = get_vendas_por_filial(qs)
    mix = get_mix_secao_categoria(qs, 10)

    # Opções para filtros (dropdowns) a partir do mesmo escopo, só por data
    qs_filtros = get_queryset_vendas(
        request.user,
        data_inicio=data_inicio,
        data_fim=data_fim,
        filter_fornecedor_as_secao=filter_fornecedor_as_secao,
    )
    filiais = list(qs_filtros.values_list('codfilial', flat=True).distinct().order_by('codfilial'))
    supervisores = list(qs_filtros.values_list('supervisor', flat=True).distinct().order_by('supervisor')[:100])
    clientes = list(qs_filtros.values_list('cliente', flat=True).distinct().exclude(cliente='').order_by('cliente')[:200])
    vendedores = list(qs_filtros.values_list('nomerca', flat=True).distinct().exclude(nomerca='').order_by('nomerca')[:200])
    if filter_fornecedor_as_secao:
        fornecedores_opcoes = list(qs_filtros.values_list('secao', flat=True).distinct().exclude(secao='').order_by('secao')[:200])
    else:
        try:
            fornecedores_opcoes = list(qs_filtros.values_list('fornecedor', flat=True).distinct().exclude(fornecedor='').order_by('fornecedor')[:200])
        except Exception:
            fornecedores_opcoes = []
    produtos = list(qs_filtros.values_list('produto', flat=True).distinct().exclude(produto='').order_by('produto')[:200])

    # Serializar para JSON nos templates (gráficos)
    def to_json(obj):
        try:
            return json.dumps(obj, default=str)
        except Exception:
            return '[]'

    context = {
        'cards': cards,
        'serie_temporal': to_json(serie),
        'top_produtos': to_json([{'produto': p['produto'], 'valor': float(p['valor'] or 0)} for p in top_produtos]),
        'top_clientes': to_json([{'cliente': c['cliente'] or '(vazio)', 'valor': float(c['valor'] or 0)} for c in top_clientes]),
        'top_fornecedores': to_json([{'fornecedor': f['fornecedor'] or '(vazio)', 'valor': float(f['valor'] or 0)} for f in top_fornecedores]),
        'vendas_por_supervisor': to_json([{'supervisor': s['supervisor'] or '(vazio)', 'valor': float(s['valor'] or 0)} for s in por_supervisor]),
        'top_vendedores': to_json([{'vendedor': v['nomerca'] or '(vazio)', 'valor': float(v['valor'] or 0)} for v in top_vendedores]),
        'vendas_por_filial': to_json([{'codfilial': f['codfilial'], 'valor': float(f['valor'] or 0)} for f in por_filial]),
        'mix_secao_categoria': mix,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'filiais': filiais,
        'supervisores': supervisores,
        'clientes': clientes,
        'vendedores': vendedores,
        'fornecedores_opcoes': fornecedores_opcoes,
        'produtos': produtos,
        'fornecedores_label': fornecedores_label,
        'pode_exportar': request.user.has_perm('relatorios.pode_exportar_excel'),
    }
    return render(request, 'relatorios/dashboard.html', context)


class RelatorioDetalhadoView(LoginRequiredMixin, ListView):
    template_name = 'relatorios/relatorio_detalhado.html'
    paginate_by = 50
    context_object_name = 'vendas'

    def get_queryset(self):
        from datetime import datetime
        from django.utils import timezone
        perm = 'relatorios.pode_ver_relatorio_vendas'
        if not (self.request.user.is_superuser or self.request.user.has_perm(perm)):
            return StgVendas.objects.none()
        hoje = timezone.now().date()
        inicio_mes = hoje.replace(day=1)
        di = self.request.GET.get('data_inicio') or None
        df = self.request.GET.get('data_fim') or None
        if di and isinstance(di, str):
            try:
                di = datetime.strptime(di, '%Y-%m-%d').date()
            except ValueError:
                di = inicio_mes
        else:
            di = di or inicio_mes
        if df and isinstance(df, str):
            try:
                df = datetime.strptime(df, '%Y-%m-%d').date()
            except ValueError:
                df = hoje
        else:
            df = df or hoje
        codfilial = (self.request.GET.get('codfilial') or '').strip() or None
        supervisor = (self.request.GET.get('supervisor') or '').strip() or None
        cliente = (self.request.GET.get('cliente') or '').strip() or None
        vendedor = (self.request.GET.get('vendedor') or '').strip() or None
        fornecedor = (self.request.GET.get('fornecedor') or '').strip() or None
        produto = (self.request.GET.get('produto') or '').strip() or None
        q = (self.request.GET.get('q') or '').strip() or None
        qs_escopo = get_queryset_vendas(self.request.user, data_inicio=di, data_fim=df)
        try:
            filter_fornecedor_as_secao = not qs_escopo.filter(fornecedor__isnull=False).exclude(fornecedor='').exists()
        except Exception:
            filter_fornecedor_as_secao = True
        qs = get_queryset_vendas(
            self.request.user,
            data_inicio=di,
            data_fim=df,
            codfilial=codfilial,
            supervisor=supervisor,
            cliente=cliente,
            vendedor=vendedor,
            fornecedor=fornecedor,
            produto=produto,
            filter_fornecedor_as_secao=filter_fornecedor_as_secao,
            q=q,
        )
        return qs.order_by('-data_faturamento')

    def get_context_data(self, **kwargs):
        from .services import get_queryset_vendas
        from datetime import datetime, timedelta
        from django.utils import timezone
        from urllib.parse import urlencode
        ctx = super().get_context_data(**kwargs)
        ctx['pode_exportar'] = self.request.user.has_perm('relatorios.pode_exportar_excel')
        hoje = timezone.now().date()
        # Padrão: mês atual (primeiro dia até hoje)
        inicio_mes = hoje.replace(day=1)
        di = self.request.GET.get('data_inicio') or inicio_mes
        df = self.request.GET.get('data_fim') or hoje
        if isinstance(di, str):
            try:
                di = datetime.strptime(di, '%Y-%m-%d').date()
            except ValueError:
                di = inicio_mes
        if isinstance(df, str):
            try:
                df = datetime.strptime(df, '%Y-%m-%d').date()
            except ValueError:
                df = hoje
        ctx['data_inicio'] = di
        ctx['data_fim'] = df
        qs = get_queryset_vendas(self.request.user, data_inicio=di, data_fim=df)
        try:
            filter_fornecedor_as_secao = not qs.filter(fornecedor__isnull=False).exclude(fornecedor='').exists()
        except Exception:
            filter_fornecedor_as_secao = True
        ctx['filiais'] = list(qs.values_list('codfilial', flat=True).distinct().order_by('codfilial'))
        ctx['supervisores'] = list(qs.values_list('supervisor', flat=True).distinct().order_by('supervisor')[:100])
        ctx['vendedores'] = list(qs.values_list('nomerca', flat=True).distinct().exclude(nomerca='').order_by('nomerca')[:200])
        ctx['clientes'] = list(qs.values_list('cliente', flat=True).distinct().exclude(cliente='').order_by('cliente')[:200])
        if filter_fornecedor_as_secao:
            ctx['fornecedores_opcoes'] = list(qs.values_list('secao', flat=True).distinct().exclude(secao='').order_by('secao')[:200])
        else:
            try:
                ctx['fornecedores_opcoes'] = list(qs.values_list('fornecedor', flat=True).distinct().exclude(fornecedor='').order_by('fornecedor')[:200])
            except Exception:
                ctx['fornecedores_opcoes'] = []
        ctx['produtos'] = list(qs.values_list('produto', flat=True).distinct().exclude(produto='').order_by('produto')[:200])
        params = {k: v for k, v in self.request.GET.items() if k != 'page'}
        ctx['export_excel_query'] = urlencode(params)
        return ctx


def export_excel_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if not request.user.has_perm('relatorios.pode_exportar_excel'):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('Sem permissão para exportar Excel.')
    from datetime import datetime
    from django.utils import timezone as tz
    hoje = tz.now().date()
    inicio_mes = hoje.replace(day=1)
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    if data_inicio and isinstance(data_inicio, str):
        try:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        except ValueError:
            data_inicio = inicio_mes
    else:
        data_inicio = data_inicio or inicio_mes
    if data_fim and isinstance(data_fim, str):
        try:
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
        except ValueError:
            data_fim = hoje
    else:
        data_fim = data_fim or hoje
    codfilial = (request.GET.get('codfilial') or '').strip() or None
    supervisor = (request.GET.get('supervisor') or '').strip() or None
    cliente = (request.GET.get('cliente') or '').strip() or None
    vendedor = (request.GET.get('vendedor') or '').strip() or None
    fornecedor = (request.GET.get('fornecedor') or '').strip() or None
    produto = (request.GET.get('produto') or '').strip() or None
    q = (request.GET.get('q') or '').strip() or None
    qs_escopo = get_queryset_vendas(request.user, data_inicio=data_inicio, data_fim=data_fim)
    try:
        filter_fornecedor_as_secao = not qs_escopo.filter(fornecedor__isnull=False).exclude(fornecedor='').exists()
    except Exception:
        filter_fornecedor_as_secao = True
    qs = get_queryset_vendas(
        request.user,
        data_inicio=data_inicio,
        data_fim=data_fim,
        codfilial=codfilial,
        supervisor=supervisor,
        cliente=cliente,
        vendedor=vendedor,
        fornecedor=fornecedor,
        produto=produto,
        filter_fornecedor_as_secao=filter_fornecedor_as_secao,
        q=q,
    )
    try:
        buffer = export_vendas_excel(qs)
        data = buffer.getvalue()
    except Exception as e:
        from django.http import HttpResponse
        return HttpResponse(
            f'Erro ao gerar Excel: {e}. Verifique os dados ou permissões.',
            status=500,
            content_type='text/plain; charset=utf-8',
        )
    response = HttpResponse(data, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="vendas.xlsx"'
    return response
