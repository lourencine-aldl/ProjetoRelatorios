# -*- coding: utf-8 -*-
from datetime import timedelta
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.core.cache import cache
from django.core.management import call_command
from django.core.paginator import Paginator, Page
from django.conf import settings
from django.contrib import messages
from io import StringIO

from .models import StgVendas


class PaginatorSemCount(Paginator):
    """Paginator que não executa COUNT(*); usa apenas LIMIT/OFFSET para a página atual."""
    has_real_count = False  # template pode mostrar só "Página N" sem total

    def __init__(self, object_list, per_page, **kwargs):
        super().__init__(object_list, per_page, **kwargs)
        self._last_page_num = None
        self._last_has_next = False
        self._last_len = 0

    @property
    def count(self):
        if self._last_page_num is None:
            return 0
        if self._last_has_next:
            return self._last_page_num * self.per_page + 1
        return (self._last_page_num - 1) * self.per_page + self._last_len

    def page(self, number):
        number = self.validate_number(number)
        start = (number - 1) * self.per_page
        # Busca só esta página + 1 para saber se há próxima (evita COUNT)
        chunk = list(self.object_list[start : start + self.per_page + 1])
        self._last_len = len(chunk)
        self._last_has_next = self._last_len > self.per_page
        self._last_page_num = number
        return Page(chunk[: self.per_page], number, self)
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


@login_required
def atualizar_dados_view(request):
    """Executa import_vendas_csv (truncate + arquivo configurado). Apenas staff."""
    if not request.user.is_staff:
        messages.error(request, 'Sem permissão para atualizar a base de dados.')
        return redirect('dashboard')
    csv_path = getattr(settings, 'IMPORT_VENDAS_CSV_PATH', None)
    if not csv_path:
        messages.error(request, 'Caminho do CSV não configurado (IMPORT_VENDAS_CSV_PATH).')
        return redirect('dashboard')
    from pathlib import Path
    path = Path(csv_path)
    if not path.is_absolute():
        path = Path(settings.BASE_DIR) / path
    if not path.exists():
        messages.error(request, f'Arquivo não encontrado: {path}')
        return redirect('dashboard')
    if request.method != 'POST':
        return render(request, 'relatorios/atualizar_dados.html', {'csv_path': path})
    out = StringIO()
    err = StringIO()
    sep = getattr(settings, 'IMPORT_VENDAS_CSV_SEP', ';')
    fmt = getattr(settings, 'IMPORT_VENDAS_CSV_FORMAT', '')
    cmd_args = [str(path), '--truncate', '--sep', sep]
    if fmt:
        cmd_args.extend(['--format', fmt])
    try:
        call_command('import_vendas_csv', *cmd_args, stdout=out, stderr=err)
        cache.clear()  # evita dashboard/relatório virem vazios por causa de cache antigo
        log = (out.getvalue() or '').strip() + (err.getvalue() or '').strip()
        messages.success(request, f'Base de dados atualizada. {log}')
    except Exception as e:
        messages.error(request, f'Erro ao importar: {e}')
    return redirect('dashboard')


def root_redirect(request):
    """Redireciona / para login ou dashboard."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


@login_required
def remover_links_pbi_usuarios_view(request):
    """
    Página no admin: selecionar usuário(s) na lista de Utilizadores → ação "Remover acesso a links PBI" →
    esta página mostra os links; marcar os que quer remover do(s) usuário(s) e enviar.
    Acesso: staff. GET: ids=1,2,3 (pk dos usuários). POST: ids + link_ids (pk dos RecursoPBI).
    """
    from django.contrib.auth import get_user_model
    from urllib.parse import urlencode

    if not request.user.is_staff:
        messages.error(request, 'Acesso restrito a administradores.')
        return redirect('admin:index')
    User = get_user_model()
    if request.method == 'POST':
        ids = request.POST.get('ids', '')
        link_ids = request.POST.getlist('link_ids')
        if not ids or not link_ids:
            messages.warning(request, 'Selecione pelo menos um usuário e um link.')
        else:
            try:
                user_pks = [int(x.strip()) for x in ids.split(',') if x.strip()]
                link_pks = [int(x) for x in link_ids if x]
                users = list(User.objects.filter(pk__in=user_pks))
                from .models import RecursoPBI
                links = list(RecursoPBI.objects.filter(pk__in=link_pks))
                for link in links:
                    for u in users:
                        link.usuarios_permitidos.remove(u)
                n_links, n_users = len(links), len(users)
                messages.success(request, f'Acesso removido: {n_users} usuário(s) sem {n_links} link(s) selecionado(s).')
            except (ValueError, TypeError) as e:
                messages.error(request, f'Dados inválidos: {e}')
        return redirect('admin:auth_user_changelist')
    ids_str = request.GET.get('ids', '')
    if not ids_str:
        messages.warning(request, 'Selecione usuário(s) na lista de Utilizadores e use a ação "Remover acesso a links PBI".')
        return redirect('admin:auth_user_changelist')
    try:
        user_pks = [int(x.strip()) for x in ids_str.split(',') if x.strip()]
    except ValueError:
        messages.error(request, 'IDs de usuários inválidos.')
        return redirect('admin:auth_user_changelist')
    users = list(User.objects.filter(pk__in=user_pks).order_by('username'))
    if not users:
        messages.warning(request, 'Nenhum usuário encontrado.')
        return redirect('admin:auth_user_changelist')
    from .models import RecursoPBI
    # Mostrar só os links a que pelo menos um dos usuários selecionados tem acesso
    links = list(
        RecursoPBI.objects.filter(usuarios_permitidos__in=users)
        .distinct()
        .order_by('ordem', 'nome')
    )
    return render(request, 'admin/relatorios/remover_links_pbi.html', {
        'users': users,
        'links': links,
        'ids': ids_str,
        'title': 'Remover acesso a links PBI',
    })


def gerir_links_usuario_view(request, user_id):
    """
    Tela: links disponíveis do usuário (só os que ele tem acesso).
    Colunas: Nome, Descrição, URL, Ordenar.
    Permite selecionar links para remover acesso e tem link para adicionar acesso (Recursos PBI).
    Acesso: staff.
    """
    from django.contrib.auth import get_user_model
    from django.urls import reverse

    if not request.user.is_staff:
        messages.error(request, 'Acesso restrito a administradores.')
        return redirect('admin:index')

    User = get_user_model()
    try:
        user_obj = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        messages.error(request, 'Usuário não encontrado.')
        return redirect('admin:auth_user_changelist')

    from .models import RecursoPBI

    if request.method == 'POST':
        links_atual = list(user_obj.recursos_pbi.all().order_by('ordem', 'nome'))
        # Salvar ordem (sempre que houver inputs ordem_<pk>)
        for link in links_atual:
            key = f'ordem_{link.pk}'
            if key in request.POST:
                try:
                    nova_ordem = int(request.POST.get(key, 0))
                    if link.ordem != nova_ordem:
                        link.ordem = nova_ordem
                        link.save(update_fields=['ordem'])
                except (ValueError, TypeError):
                    pass
        # Remover acesso dos selecionados (se o botão foi usado)
        link_ids = request.POST.getlist('link_ids')
        if link_ids:
            try:
                link_pks = [int(x) for x in link_ids if x]
                links = RecursoPBI.objects.filter(pk__in=link_pks)
                for link in links:
                    link.usuarios_permitidos.remove(user_obj)
                n = links.count()
                messages.success(request, f'Acesso removido a {n} link(s) e ordem atualizada.')
            except (ValueError, TypeError):
                messages.error(request, 'Dados inválidos.')
        else:
            if any(f'ordem_{l.pk}' in request.POST for l in links_atual):
                messages.success(request, 'Ordem de exibição atualizada.')
        return redirect('admin_gerir_links_usuario', user_id=user_id)

    links = list(user_obj.recursos_pbi.all().order_by('ordem', 'nome'))
    add_access_url = reverse('admin:relatorios_recursopbi_changelist')
    edit_user_url = reverse('admin:auth_user_change', args=[user_obj.pk])

    return render(request, 'admin/relatorios/gerir_links_usuario.html', {
        'title': f'Links do usuário «{user_obj.username}»',
        'user_obj': user_obj,
        'links': links,
        'add_access_url': add_access_url,
        'edit_user_url': edit_user_url,
    })


def teste_web_view(request):
    """Página de teste (sem login) para verificar se a aplicação está no ar."""
    from django.utils import timezone
    agora = timezone.now().strftime('%d/%m/%Y %H:%M:%S')
    html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><title>Teste - App Relatórios</title></head>
<body style="font-family:sans-serif;max-width:600px;margin:3rem auto;padding:1rem;">
  <h1>✓ Aplicação funcionando</h1>
  <p>Servidor respondeu com sucesso.</p>
  <p><strong>Data/hora do servidor:</strong> {agora}</p>
  <p><a href="/login/">Ir para login</a></p>
</body>
</html>'''
    return HttpResponse(html, content_type='text/html; charset=utf-8')


@login_required
def dashboard_pbi(request):
    """Página com opções para abrir relatórios Power BI. Acesso: permissão pode_ver_power_bi OU ter pelo menos um recurso PBI atribuído.
    Só exibe os recursos (links) aos quais o usuário foi permitido no admin (Recursos PBI)."""
    perm = 'relatorios.pode_ver_power_bi'
    tem_permissao = request.user.is_superuser or request.user.has_perm(perm)
    tem_recursos = request.user.recursos_pbi.exists()
    if not (tem_permissao or tem_recursos):
        return render(request, 'relatorios/sem_permissao.html')
    from .models import RecursoPBI
    # Superusuário ou staff (acesso admin): vê todos os recursos. Demais usuários: só os que têm na lista "Usuários com acesso".
    if request.user.is_superuser or request.user.is_staff:
        qs = RecursoPBI.objects.all().order_by('ordem', 'nome')
    else:
        qs = RecursoPBI.objects.filter(usuarios_permitidos=request.user).distinct().order_by('ordem', 'nome')
    reports = [
        {'id': f'r-{r.pk}', 'nome': r.nome, 'descricao': r.descricao or '', 'url': r.url}
        for r in qs
    ]
    return render(request, 'relatorios/dashboard_pbi.html', {'reports': reports})


@login_required
def dashboard(request):
    perm = 'relatorios.pode_ver_relatorio_vendas'
    if not (request.user.is_superuser or request.user.has_perm(perm)):
        return render(request, 'relatorios/sem_permissao.html')

    hoje = timezone.now().date()
    from datetime import date
    # Padrão: mês atual (dia 1 até hoje). Usuário pode alterar pelo filtro para ver outros períodos.
    inicio_mes = date(hoje.year, hoje.month, 1)
    usuario_escolheu_data = 'data_inicio' in request.GET or 'data_fim' in request.GET
    data_fim = request.GET.get('data_fim') or hoje
    data_inicio = request.GET.get('data_inicio') or inicio_mes
    if isinstance(data_inicio, str):
        try:
            from datetime import datetime
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        except ValueError:
            data_inicio = inicio_mes
    if isinstance(data_fim, str):
        try:
            from datetime import datetime
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
        except ValueError:
            data_fim = hoje
    # Padrão: mês atual. Limpar filtros = mês atual.
    qs_escopo = get_queryset_vendas(request.user, data_inicio=data_inicio, data_fim=data_fim)
    try:
        filter_fornecedor_as_secao = not qs_escopo.filter(fornecedor__isnull=False).exclude(fornecedor='').exists()
    except Exception:
        filter_fornecedor_as_secao = True

    def _list_or_none(name):
        L = [x.strip() for x in request.GET.getlist(name) if x and str(x).strip()]
        return L if L else None
    codfilial = _list_or_none('codfilial')
    supervisor = _list_or_none('supervisor')
    secao = request.GET.get('secao', '').strip() or None
    categoria = request.GET.get('categoria', '').strip() or None
    cliente = _list_or_none('cliente')
    vendedor = _list_or_none('vendedor')
    fornecedor = _list_or_none('fornecedor')
    produto = _list_or_none('produto')
    q = request.GET.get('q', '').strip() or None

    # Cache: mesma combinação de datas + filtros = resposta em cache (2 min). ?nocache=1 ignora cache.
    cache_key = 'relatorios:dashboard:%s:%s:%s:%s' % (
        request.user.pk,
        data_inicio,
        data_fim,
        tuple(sorted((k, v) for k, v in request.GET.items() if v and k != 'nocache')),
    )
    cached = None if request.GET.get('nocache') else cache.get(cache_key)
    if cached is not None:
        # Se cache tem cards com vendas mas gráficos vazios, ignorar e recalcular
        try:
            tv = (cached.get('cards') or {}).get('total_vendido')
            total = float(tv) if tv is not None else 0.0
        except (TypeError, ValueError):
            total = 0.0
        has_chart_data = len(cached.get('serie_temporal') or []) > 0 and len(cached.get('top_clientes') or []) > 0
        if total > 0 and not has_chart_data:
            cached = None
    if cached is not None:
        agrupamento = request.GET.get('agrupamento', 'dia')
        context = {
            **cached,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'agrupamento': agrupamento,
            'pode_exportar': request.user.has_perm('relatorios.pode_exportar_excel'),
        }
        for key in ('serie_temporal', 'top_clientes', 'top_fornecedores', 'top_produtos', 'vendas_por_supervisor', 'top_vendedores'):
            if context.get(key) is None:
                context[key] = []
        context['selected_supervisores'] = request.GET.getlist('supervisor')
        context['selected_clientes'] = request.GET.getlist('cliente')
        context['selected_vendedores'] = request.GET.getlist('vendedor')
        context['selected_fornecedores'] = request.GET.getlist('fornecedor')
        context['selected_produtos'] = request.GET.getlist('produto')
        context['selected_filiais'] = request.GET.getlist('codfilial')
        # Título sempre curto (sem "rolar para ver mais")
        lbl = (context.get('fornecedores_label') or '')
        for s in (' (rolar para ver mais)', '(rolar para ver mais)'):
            lbl = lbl.replace(s, '')
        context['fornecedores_label'] = lbl.strip() or 'Top 10 fornecedores'
        context['fornecedores_titulo'] = 'Top 10 fornecedores / seção' if 'seção' in (lbl or '') else 'Top 10 fornecedores'
        return render(request, 'relatorios/dashboard.html', context)

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
    divisor = getattr(settings, 'VALOR_DIVISOR', 1000)
    # Cards para exibição: valores monetários divididos por VALOR_DIVISOR (banco em escala 1000x)
    cards_display = dict(cards)
    for key in ('total_vendido', 'ticket_medio', 'devolucao', 'bonificacao'):
        if key in cards_display and cards_display[key] is not None:
            try:
                cards_display[key] = float(cards_display[key]) / divisor
            except (TypeError, ValueError):
                pass
    agrupamento = request.GET.get('agrupamento', 'dia')
    serie = get_serie_temporal(qs, agrupamento)
    # Se a série está vazia mas há vendas (ex.: data_faturamento nula), mostrar pelo menos o total
    if not serie and qs.exists():
        from django.db.models import Sum, F
        from django.db.models.functions import Coalesce
        from django.db.models import Value, DecimalField
        from decimal import Decimal
        _dec = DecimalField(max_digits=16, decimal_places=4)
        total = qs.aggregate(s=Sum(Coalesce(F('valor_liquido'), Value(Decimal('0'), output_field=_dec), output_field=_dec)))['s'] or 0
        serie = [{'periodo': str(data_inicio), 'valor': float(total), 'label': 'Total (sem data)'}]
    # Labels no eixo X: por mês = MM/AA, por dia = 01/jan/26
    meses_abrev = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
    for item in serie:
        p = item.get('periodo') or ''
        try:
            from datetime import datetime
            s = str(p)[:10]
            if len(s) >= 10:
                dt = datetime.strptime(s, '%Y-%m-%d')
                if agrupamento == 'ano':
                    item['label'] = dt.strftime('%Y')
                elif agrupamento == 'mes':
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
    fornecedores_label = 'Top 10 fornecedores'
    if filter_fornecedor_as_secao:
        top_secoes = get_top_secoes(qs, 50)
        top_fornecedores = [{'fornecedor': s.get('secao') or '(sem seção)', 'valor': s.get('valor')} for s in top_secoes]
        fornecedores_label = 'Top 10 fornecedores / seção'
    top_produtos = get_top_produtos(qs, 50)
    por_supervisor = get_vendas_por_supervisor(qs, 50)
    top_vendedores = get_top_vendedores(qs, 50)
    por_filial = get_vendas_por_filial(qs)
    mix = get_mix_secao_categoria(qs, 10)

    # Opções dos filtros: tentar cache por (user, período, fornecedor/seção) para evitar 6 consultas
    filtros_cache_key = 'relatorios:filtros:%s:%s:%s:%s' % (request.user.pk, data_inicio, data_fim, filter_fornecedor_as_secao)
    filtros_cached = cache.get(filtros_cache_key)
    if filtros_cached is not None:
        filiais, supervisores, clientes, vendedores, fornecedores_opcoes, produtos = filtros_cached
        # Compat: cache antigo tinha clientes como lista de strings
        if clientes and isinstance(clientes[0], str):
            clientes = [{'codcliente': '', 'cliente': c, 'value': c} for c in clientes]
    else:
        filiais = list(qs_escopo.values_list('codfilial', flat=True).distinct().order_by('codfilial'))
        supervisores = list(qs_escopo.values_list('supervisor', flat=True).distinct().order_by('supervisor')[:100])
        clientes_raw = list(qs_escopo.values('codcliente', 'cliente', 'cliente_formatado').distinct().exclude(cliente='').order_by('cliente')[:1000])
        def _cliente_display(x):
            fmt = (x.get('cliente_formatado') or '').strip()
            if fmt:
                return fmt
            cod, nome = (x.get('codcliente') or '').strip(), (x.get('cliente') or '').strip()
            return (cod + ' - ' + nome) if cod else (nome or '')
        clientes = [{'codcliente': (x.get('codcliente') or ''), 'cliente': _cliente_display(x), 'value': (x.get('codcliente') or '') + '|' + (x.get('cliente') or '')} for x in clientes_raw]
        vendedores = list(qs_escopo.values_list('nomerca', flat=True).distinct().exclude(nomerca='').order_by('nomerca')[:200])
        if filter_fornecedor_as_secao:
            fornecedores_opcoes = list(qs_escopo.values_list('secao', flat=True).distinct().exclude(secao='').order_by('secao')[:200])
        else:
            try:
                fornecedores_opcoes = list(qs_escopo.values_list('fornecedor', flat=True).distinct().exclude(fornecedor='').order_by('fornecedor')[:200])
            except Exception:
                fornecedores_opcoes = []
        produtos = list(qs_escopo.values_list('produto', flat=True).distinct().exclude(produto='').order_by('produto')[:200])
        cache.set(filtros_cache_key, (filiais, supervisores, clientes, vendedores, fornecedores_opcoes, produtos), timeout=180)

    # Dados para gráficos: listas serializáveis (template usa json_script para evitar quebra no HTML)
    def as_float(v):
        try:
            return float(v) if v is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    chart_serie_temporal = [{'periodo': str(item.get('periodo', '')), 'valor': as_float(item.get('valor')) / divisor, 'label': str(item.get('label', ''))} for item in serie]
    chart_top_produtos = [{'produto': str(p.get('produto', '')), 'valor': as_float(p.get('valor')) / divisor} for p in top_produtos]
    # Gráfico de clientes: usa CLIENTE_FORMATADO (coluna do CSV) quando preenchido, senão "CodCli - Cliente" (display)
    def _cliente_chart_label(c):
        fmt = (c.get('cliente_formatado') or '').strip()
        if fmt:
            return fmt
        disp = (c.get('display') or '').strip()
        if disp:
            return disp
        cod, nome = (c.get('codcliente') or '').strip(), (c.get('cliente') or '').strip()
        return (cod + ' - ' + nome) if (cod or nome) else '(vazio)'

    def _cliente_filter_value(c):
        cod, nome = (c.get('codcliente') or '').strip(), (c.get('cliente') or '').strip()
        return (cod + '|' + nome) if (cod or nome) else ''

    chart_top_clientes = [
        {'cliente': _cliente_chart_label(c), 'valor': as_float(c.get('valor')) / divisor, 'cliente_value': _cliente_filter_value(c)}
        for c in top_clientes
    ]
    chart_top_fornecedores = [{'fornecedor': str(f.get('fornecedor') or '(vazio)'), 'valor': as_float(f.get('valor')) / divisor} for f in top_fornecedores]
    chart_supervisor = [{'supervisor': str(s.get('supervisor') or '(vazio)'), 'valor': as_float(s.get('valor')) / divisor} for s in por_supervisor]
    chart_vendedores = [{'vendedor': str(v.get('nomerca') or '(vazio)'), 'valor': as_float(v.get('valor')) / divisor} for v in top_vendedores]

    # Garantir listas (nunca None) para o template/json_script
    def as_list(val):
        return list(val) if val is not None else []

    # Se período sem dados, buscar intervalo real na base para orientar o usuário (só quando não veio de clique no gráfico)
    periodo_disponivel = None
    try:
        total = float(cards.get('total_vendido') or 0) / divisor
    except (TypeError, ValueError):
        total = 0.0
    # Não mostrar a mensagem quando o usuário já aplicou filtros (ex.: clicou em cliente no gráfico)
    usuario_aplicou_filtros = bool(request.GET.getlist('cliente') or request.GET.getlist('supervisor') or request.GET.getlist('vendedor') or request.GET.getlist('fornecedor') or request.GET.getlist('produto') or request.GET.getlist('codfilial'))
    if total == 0 and not usuario_aplicou_filtros:
        from django.db.models import Min, Max
        qs_base = get_queryset_vendas(request.user, data_inicio=None, data_fim=None)
        agg = qs_base.aggregate(Min('data_faturamento'), Max('data_faturamento'))
        min_dt, max_dt = agg.get('data_faturamento__min'), agg.get('data_faturamento__max')
        if min_dt and max_dt:
            periodo_disponivel = (
                min_dt.date() if hasattr(min_dt, 'date') else min_dt,
                max_dt.date() if hasattr(max_dt, 'date') else max_dt,
            )

    context = {
        'cards': cards_display,
        'serie_temporal': as_list(chart_serie_temporal),
        'top_produtos': as_list(chart_top_produtos),
        'top_clientes': as_list(chart_top_clientes),
        'top_fornecedores': as_list(chart_top_fornecedores),
        'vendas_por_supervisor': as_list(chart_supervisor),
        'top_vendedores': as_list(chart_vendedores),
        'vendas_por_filial': [{'codfilial': f['codfilial'], 'valor': as_float(f.get('valor')) / divisor} for f in por_filial],
        'mix_secao_categoria': mix,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'agrupamento': agrupamento,
        'filiais': filiais,
        'supervisores': supervisores,
        'clientes': clientes,
        'vendedores': vendedores,
        'fornecedores_opcoes': fornecedores_opcoes,
        'produtos': produtos,
        'fornecedores_label': fornecedores_label,
        'fornecedores_titulo': fornecedores_label,  # já curto aqui
        'periodo_disponivel': periodo_disponivel,
    }
    context['pode_exportar'] = request.user.has_perm('relatorios.pode_exportar_excel')
    context['selected_supervisores'] = request.GET.getlist('supervisor')
    context['selected_clientes'] = request.GET.getlist('cliente')
    context['selected_vendedores'] = request.GET.getlist('vendedor')
    context['selected_fornecedores'] = request.GET.getlist('fornecedor')
    context['selected_produtos'] = request.GET.getlist('produto')
    context['selected_filiais'] = request.GET.getlist('codfilial')
    # Não cachear resultado vazio: assim, quando houver dados no mês, a próxima carga mostra
    if total > 0:
        cache.set(cache_key, context, timeout=120)
    return render(request, 'relatorios/dashboard.html', context)


def _normalize_for_search(s):
    """Remove acentos para busca case/accent insensitive."""
    import unicodedata
    if not s:
        return ''
    n = unicodedata.normalize('NFD', str(s))
    return ''.join(c for c in n if unicodedata.category(c) != 'Mn').lower().strip()


@login_required
def api_busca_clientes(request):
    """API JSON: busca clientes por texto (para filtro com muitos clientes). GET: q, data_inicio, data_fim. Retorna até 100 nomes."""
    if not request.user.has_perm('relatorios.pode_ver_relatorio_vendas'):
        return JsonResponse({'clientes': []})
    hoje = timezone.now().date()
    from datetime import date, datetime
    inicio_mes = date(hoje.year, hoje.month, 1)
    data_inicio = request.GET.get('data_inicio') or inicio_mes
    data_fim = request.GET.get('data_fim') or hoje
    if isinstance(data_inicio, str):
        try:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        except ValueError:
            data_inicio = inicio_mes
    if isinstance(data_fim, str):
        try:
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
        except ValueError:
            data_fim = hoje
    qs = get_queryset_vendas(request.user, data_inicio=data_inicio, data_fim=data_fim)
    q = (request.GET.get('q') or '').strip()

    # Formato filtro: usa cliente_formatado (CSV) para exibição quando preenchido, senão "CodCli - Cliente"
    def _row(cod, nome, formato=None):
        cod = str(cod or '').strip()
        nome = str(nome or '').strip()
        fmt = str(formato or '').strip()
        val = cod + '|' + nome
        lab = fmt if fmt else ((cod + ' - ' + nome) if cod else (nome or ''))
        return {'value': val, 'label': lab}

    if not q:
        rows = list(qs.values('codcliente', 'cliente', 'cliente_formatado').distinct().exclude(cliente='').order_by('codcliente', 'cliente')[:50])
        clientes = [_row(r.get('codcliente'), r.get('cliente'), r.get('cliente_formatado')) for r in rows]
        return JsonResponse({'clientes': clientes})
    q_normalized = _normalize_for_search(q)
    from django.db.models import Q
    candidates = list(
        qs.values('codcliente', 'cliente', 'cliente_formatado')
        .distinct()
        .exclude(cliente='')
        .filter(Q(cliente__icontains=q) | Q(cliente_formatado__icontains=q) | Q(codcliente__icontains=q))[:2000]
    )
    out = [
        _row(r.get('codcliente'), r.get('cliente'), r.get('cliente_formatado'))
        for r in candidates
        if q_normalized in _normalize_for_search(r.get('cliente') or '')
        or q_normalized in _normalize_for_search(r.get('cliente_formatado') or '')
        or q_normalized in _normalize_for_search(r.get('codcliente') or '')
    ][:100]
    return JsonResponse({'clientes': out})


class RelatorioDetalhadoView(LoginRequiredMixin, ListView):
    template_name = 'relatorios/relatorio_detalhado.html'
    paginate_by = 50
    context_object_name = 'vendas'

    def get_paginator(self, queryset, per_page, orphans=0, allow_empty_first_page=True):
        return PaginatorSemCount(queryset, per_page)

    def get_queryset(self):
        from datetime import datetime, date, timedelta
        from django.utils import timezone
        perm = 'relatorios.pode_ver_relatorio_vendas'
        if not (self.request.user.is_superuser or self.request.user.has_perm(perm)):
            return StgVendas.objects.none()
        hoje = timezone.now().date()
        inicio_mes = date(hoje.year, hoje.month, 1)
        usuario_escolheu_data = 'data_inicio' in self.request.GET or 'data_fim' in self.request.GET
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
        # Padrão: mês atual. Limpar filtros = mês atual.
        qs_escopo = get_queryset_vendas(self.request.user, data_inicio=di, data_fim=df)
        try:
            filter_fornecedor_as_secao = not qs_escopo.filter(fornecedor__isnull=False).exclude(fornecedor='').exists()
        except Exception:
            filter_fornecedor_as_secao = True
        # Guardar para get_context_data (evita nova get_queryset_vendas)
        self._relatorio_qs_filtros = qs_escopo
        self._relatorio_di, self._relatorio_df = di, df
        self._relatorio_filter_fornecedor_as_secao = filter_fornecedor_as_secao

        def _list(name):
            L = [x.strip() for x in self.request.GET.getlist(name) if x and str(x).strip()]
            return L if L else None
        codfilial = _list('codfilial')
        supervisor = _list('supervisor')
        cliente = _list('cliente')
        vendedor = _list('vendedor')
        fornecedor = _list('fornecedor')
        produto = _list('produto')
        q = (self.request.GET.get('q') or '').strip() or None
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
        cols = ('id', 'data_faturamento', 'numnota', 'codcliente', 'cliente', 'cliente_formatado', 'codfilial', 'nomerca', 'supervisor', 'produto', 'qtd', 'valortotal', 'vldevolucao')
        order_allowed = {'data_faturamento', 'numnota', 'codcliente', 'cliente', 'cliente_formatado', 'codfilial', 'nomerca', 'supervisor', 'produto', 'qtd', 'valortotal', 'vldevolucao'}
        order = (self.request.GET.get('order') or '-data_faturamento').strip()
        order_field = order.lstrip('-') if order.startswith('-') else order
        if order_field not in order_allowed:
            order = '-data_faturamento'
        return qs.only(*cols).order_by(order)

    def get_context_data(self, **kwargs):
        from urllib.parse import urlencode
        ctx = super().get_context_data(**kwargs)
        ctx['pode_exportar'] = self.request.user.has_perm('relatorios.pode_exportar_excel')
        qs = getattr(self, '_relatorio_qs_filtros', None)
        di = getattr(self, '_relatorio_di', None)
        df = getattr(self, '_relatorio_df', None)
        filter_fornecedor_as_secao = getattr(self, '_relatorio_filter_fornecedor_as_secao', True)
        if qs is None:
            from .services import get_queryset_vendas
            from datetime import datetime, date as date_type, timedelta
            from django.utils import timezone
            hoje = timezone.now().date()
            inicio_mes = date_type(hoje.year, hoje.month, 1)
            usuario_escolheu_data = 'data_inicio' in self.request.GET or 'data_fim' in self.request.GET
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
            qs = get_queryset_vendas(self.request.user, data_inicio=di, data_fim=df)
            try:
                filter_fornecedor_as_secao = not qs.filter(fornecedor__isnull=False).exclude(fornecedor='').exists()
            except Exception:
                filter_fornecedor_as_secao = True
        ctx['data_inicio'] = di
        ctx['data_fim'] = df
        ctx['agrupamento'] = self.request.GET.get('agrupamento', 'dia')
        # Cache das opções de filtro (evita 6 consultas DISTINCT por request). ?nocache=1 ignora cache.
        filtros_key = 'relatorios:relatorio_filtros:%s:%s:%s:%s' % (self.request.user.pk, di, df, filter_fornecedor_as_secao)
        filtros_cached = None if self.request.GET.get('nocache') else cache.get(filtros_key)
        if filtros_cached is not None:
            ctx['filiais'], ctx['supervisores'], ctx['vendedores'], ctx['clientes'], ctx['fornecedores_opcoes'], ctx['produtos'] = filtros_cached
            if ctx['clientes'] and isinstance(ctx['clientes'][0], str):
                ctx['clientes'] = [{'codcliente': '', 'cliente': c, 'value': c} for c in ctx['clientes']]
        else:
            ctx['filiais'] = list(qs.values_list('codfilial', flat=True).distinct().order_by('codfilial'))
            ctx['supervisores'] = list(qs.values_list('supervisor', flat=True).distinct().order_by('supervisor')[:100])
            ctx['vendedores'] = list(qs.values_list('nomerca', flat=True).distinct().exclude(nomerca='').order_by('nomerca')[:200])
            clientes_raw = list(qs.values('codcliente', 'cliente', 'cliente_formatado').distinct().exclude(cliente='').order_by('cliente')[:1000])
            def _cliente_display(x):
                fmt = (x.get('cliente_formatado') or '').strip()
                if fmt:
                    return fmt
                cod, nome = (x.get('codcliente') or '').strip(), (x.get('cliente') or '').strip()
                return (cod + ' - ' + nome) if cod else (nome or '')
            ctx['clientes'] = [{'codcliente': (x.get('codcliente') or ''), 'cliente': _cliente_display(x), 'value': (x.get('codcliente') or '') + '|' + (x.get('cliente') or '')} for x in clientes_raw]
            if filter_fornecedor_as_secao:
                ctx['fornecedores_opcoes'] = list(qs.values_list('secao', flat=True).distinct().exclude(secao='').order_by('secao')[:200])
            else:
                try:
                    ctx['fornecedores_opcoes'] = list(qs.values_list('fornecedor', flat=True).distinct().exclude(fornecedor='').order_by('fornecedor')[:200])
                except Exception:
                    ctx['fornecedores_opcoes'] = []
            ctx['produtos'] = list(qs.values_list('produto', flat=True).distinct().exclude(produto='').order_by('produto')[:200])
            cache.set(filtros_key, (ctx['filiais'], ctx['supervisores'], ctx['vendedores'], ctx['clientes'], ctx['fornecedores_opcoes'], ctx['produtos']), timeout=180)
        params = {k: v for k, v in self.request.GET.items() if k != 'page'}
        ctx['export_excel_query'] = urlencode(params)
        # URLs de ordenação por coluna (preservam filtros)
        order = (self.request.GET.get('order') or '-data_faturamento').strip()
        sort_columns = [
            ('Data e hora', 'data_faturamento'),
            ('Nota', 'numnota'),
            ('CodCli', 'codcliente'),
            ('Cliente', 'cliente'),
            ('Filial', 'codfilial'),
            ('Vendedor', 'nomerca'),
            ('Supervisor', 'supervisor'),
            ('Produto', 'produto'),
            ('Qtd', 'qtd'),
            ('Valor total', 'valortotal'),
            ('Devolução', 'vldevolucao'),
        ]
        sort_headers = []
        for label, field in sort_columns:
            p_asc = self.request.GET.copy()
            p_asc['order'] = field
            if 'page' in p_asc:
                del p_asc['page']
            p_desc = self.request.GET.copy()
            p_desc['order'] = '-' + field
            if 'page' in p_desc:
                del p_desc['page']
            sort_headers.append({
                'label': label,
                'field': field,
                'url_asc': self.request.path + '?' + p_asc.urlencode(),
                'url_desc': self.request.path + '?' + p_desc.urlencode(),
                'is_asc': order == field,
                'is_desc': order == '-' + field,
                'num': field in ('qtd', 'valortotal', 'vldevolucao'),
            })
        ctx['sort_headers'] = sort_headers
        # Totalizador (Qtd, Valor total, Devolução, Positivação) sobre o mesmo queryset filtrado
        from django.db.models import Sum
        from .services import get_positividade
        qs_totais = self.get_queryset()
        ag = qs_totais.aggregate(Sum('qtd'), Sum('valortotal'), Sum('vldevolucao'))
        ctx['total_qtd'] = ag['qtd__sum'] or 0
        ctx['total_valortotal'] = ag['valortotal__sum'] or 0
        ctx['total_vldevolucao'] = ag['vldevolucao__sum'] or 0
        ctx['positividade'] = get_positividade(qs_totais)
        ctx['selected_supervisores'] = self.request.GET.getlist('supervisor')
        ctx['selected_clientes'] = self.request.GET.getlist('cliente')
        ctx['selected_vendedores'] = self.request.GET.getlist('vendedor')
        ctx['selected_fornecedores'] = self.request.GET.getlist('fornecedor')
        ctx['selected_produtos'] = self.request.GET.getlist('produto')
        ctx['selected_filiais'] = self.request.GET.getlist('codfilial')
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
    from datetime import date as date_type
    inicio_mes = date_type(hoje.year, hoje.month, 1)
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
    # Padrão: mês atual
    def _list(name):
        L = [x.strip() for x in request.GET.getlist(name) if x and str(x).strip()]
        return L if L else None
    codfilial = _list('codfilial')
    supervisor = _list('supervisor')
    cliente = _list('cliente')
    vendedor = _list('vendedor')
    fornecedor = _list('fornecedor')
    produto = _list('produto')
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
    LIMITE_EXPORT_EXCEL = 60000
    if list(qs[LIMITE_EXPORT_EXCEL : LIMITE_EXPORT_EXCEL + 1]):
        messages.error(
            request,
            'Não é possível exportar mais de 60.000 linhas. O relatório selecionado excede esse limite. Ajuste os filtros (data, filial, etc.) para reduzir a quantidade de registros.',
        )
        from urllib.parse import urlencode
        return redirect('relatorio_detalhado' + ('?' + urlencode(request.GET) if request.GET else ''))
    try:
        buffer = export_vendas_excel(qs[:LIMITE_EXPORT_EXCEL])
        data = buffer.getvalue()
    except Exception as e:
        return HttpResponse(
            f'Erro ao gerar Excel: {e}. Verifique os dados ou permissões.',
            status=500,
            content_type='text/plain; charset=utf-8',
        )
    response = HttpResponse(data, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="vendas.xlsx"'
    return response
