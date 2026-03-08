# -*- coding: utf-8 -*-
"""Context processors para templates (ex.: mostrar menu Dashboard PBI)."""


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
