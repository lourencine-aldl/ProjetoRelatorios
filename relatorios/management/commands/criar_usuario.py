# -*- coding: utf-8 -*-
"""
Cria usuário com permissões básicas (sem Power BI).
Uso: python manage.py criar_usuario lourencine 212114
     python manage.py criar_usuario lourencine 212114 --no-pbi  (default: sem PBI)
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from relatorios.models import StgVendas


class Command(BaseCommand):
    help = 'Cria usuário com acesso ao Dashboard/Relatório, sem acesso ao Power BI'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Nome de usuário')
        parser.add_argument('password', type=str, help='Senha')
        parser.add_argument(
            '--com-pbi',
            action='store_true',
            help='Incluir permissão para ver Dashboard Power BI (default: sem PBI)',
        )

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        com_pbi = options.get('com_pbi', False)
        User = get_user_model()

        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
            self.stdout.write(self.style.WARNING(f'Usuário "{username}" já existe. Atualizando permissões.'))
        else:
            user = User.objects.create_user(username=username, password=password)
            self.stdout.write(self.style.SUCCESS(f'Usuário "{username}" criado.'))

        user.set_password(password)
        user.save()

        ct = ContentType.objects.get_for_model(StgVendas)
        # Remover todas as permissões do app relatorios
        user.user_permissions.remove(
            *list(user.user_permissions.filter(content_type=ct))
        )
        # Conceder: ver relatório de vendas (dashboard + relatório)
        perm_vendas = Permission.objects.get(content_type=ct, codename='pode_ver_relatorio_vendas')
        user.user_permissions.add(perm_vendas)
        if com_pbi:
            perm_pbi = Permission.objects.get(content_type=ct, codename='pode_ver_power_bi')
            user.user_permissions.add(perm_pbi)
            self.stdout.write(self.style.SUCCESS('Permissões: Dashboard, Relatório, Power BI.'))
        else:
            self.stdout.write(self.style.SUCCESS('Permissões: Dashboard e Relatório (sem Power BI).'))

        self.stdout.write(self.style.SUCCESS(f'Login: {username} / (senha informada)'))
