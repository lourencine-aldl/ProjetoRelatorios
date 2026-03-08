# -*- coding: utf-8 -*-
"""
Atribui os links PBI existentes a todos os usuários que já têm permissão
"Pode ver Dashboard Power BI". Use depois para dar acesso aos links a quem já existe.

Uso: python manage.py atribuir_links_pbi_usuarios

Depois, no Admin → Recursos PBI (links), você pode remover algum usuário
de um link específico (ex.: tirar lourencine do link "Diretoria").
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from relatorios.models import RecursoPBI, StgVendas


class Command(BaseCommand):
    help = 'Atribui todos os links PBI existentes aos usuários que têm permissão Pode ver Dashboard Power BI'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apenas-superuser',
            action='store_true',
            help='Atribuir links apenas a superusuários (útil para teste)',
        )

    def handle(self, *args, **options):
        User = get_user_model()
        apenas_superuser = options.get('apenas_superuser', False)

        # Usuários que podem ver PBI: superuser ou têm a permissão
        if apenas_superuser:
            usuarios = list(User.objects.filter(is_superuser=True))
        else:
            ct = ContentType.objects.get_for_model(StgVendas)
            perm = Permission.objects.filter(content_type=ct, codename='pode_ver_power_bi').first()
            if not perm:
                self.stdout.write(self.style.ERROR('Permissão pode_ver_power_bi não encontrada.'))
                return
            ids_usuarios = set(
                User.objects.filter(is_superuser=True).values_list('pk', flat=True)
            ) | set(
                User.objects.filter(user_permissions=perm).values_list('pk', flat=True)
            )
            usuarios = list(User.objects.filter(pk__in=ids_usuarios))

        recursos = list(RecursoPBI.objects.all())
        if not recursos:
            self.stdout.write(self.style.WARNING('Nenhum link PBI cadastrado. Crie em Admin → Recursos PBI (links).'))
            return
        if not usuarios:
            self.stdout.write(self.style.WARNING('Nenhum usuário com permissão PBI encontrado.'))
            return

        for recurso in recursos:
            antes = recurso.usuarios_permitidos.count()
            recurso.usuarios_permitidos.add(*usuarios)
            depois = recurso.usuarios_permitidos.count()
            self.stdout.write(
                self.style.SUCCESS(
                    f'  "{recurso.nome}": {antes} → {depois} usuários com acesso'
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nPronto. {len(usuarios)} usuário(s) com PBI agora têm acesso a todos os {len(recursos)} link(s).'
            )
        )
        self.stdout.write(
            'Para restringir (ex.: tirar alguém do link "Diretoria"), use Admin → Recursos PBI (links).'
        )
