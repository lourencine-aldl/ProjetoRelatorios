# -*- coding: utf-8 -*-
"""Context processors para templates (ex.: mostrar menu Dashboard PBI, dados da sidebar)."""


def sidebar_filters_default(request):
    """
    Garante variáveis da sidebar de filtros em todas as páginas (para o include _sidebar_filters.html).
    As views (dashboard, relatorio_detalhado) sobrescrevem com dados reais; as demais usam listas vazias.
    """
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {}
    return {
        'clientes': [],
        'fornecedores_opcoes': [],
        'produtos': [],
        'selected_clientes': [],
        'selected_fornecedores': [],
        'selected_produtos': [],
    }


def pbi_menu(request):
    """
    Adiciona show_pbi_menu ao contexto: True se o usuário pode ver o link
    "Dashboard PBI" na barra lateral (tem permissão OU tem pelo menos um recurso PBI).
    """
    show = False
    if request.user.is_authenticated:
        if request.user.is_superuser:
            show = True
        elif request.user.has_perm('relatorios.pode_ver_power_bi'):
            show = True
        elif request.user.recursos_pbi.exists():
            show = True
    return {'show_pbi_menu': show}
