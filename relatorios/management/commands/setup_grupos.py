# -*- coding: utf-8 -*-
"""
Cria grupos e atribui permissões do app relatorios.
Uso: python manage.py setup_grupos
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from relatorios.models import StgVendas


class Command(BaseCommand):
    help = 'Cria grupos (admin, gestor, vendas, leitura) e atribui permissões'

    def handle(self, *args, **options):
        ct = ContentType.objects.get_for_model(StgVendas)
        perms = list(Permission.objects.filter(content_type=ct))

        grupos_config = {
            'admin': [
                'pode_ver_relatorio_vendas',
                'pode_exportar_excel',
                'pode_ver_todas_filiais',
                'pode_ver_power_bi',
            ],
            'gestor': [
                'pode_ver_relatorio_vendas',
                'pode_exportar_excel',
                'pode_ver_todas_filiais',
                'pode_ver_power_bi',
            ],
            'vendas': [
                'pode_ver_relatorio_vendas',
                'pode_exportar_excel',
            ],
            'leitura': [
                'pode_ver_relatorio_vendas',
            ],
        }

        for nome, codenames in grupos_config.items():
            grupo, created = Group.objects.get_or_create(name=nome)
            for codename in codenames:
                p = next((x for x in perms if x.codename == codename), None)
                if p:
                    grupo.permissions.add(p)
            self.stdout.write(self.style.SUCCESS(f'Grupo "{nome}" configurado.'))

        self.stdout.write(self.style.SUCCESS('Setup de grupos concluído. Atribua usuários aos grupos no Admin.'))
