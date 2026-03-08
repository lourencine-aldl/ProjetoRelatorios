# -*- coding: utf-8 -*-
from django.db import migrations

# Tradução dos nomes das permissões do auth (User e Group) para português
AUTH_PERMISSIONS_PT = {
    'add_user': 'Pode adicionar usuário',
    'change_user': 'Pode alterar usuário',
    'delete_user': 'Pode excluir usuário',
    'view_user': 'Pode ver usuário',
    'add_group': 'Pode adicionar grupo',
    'change_group': 'Pode alterar grupo',
    'delete_group': 'Pode excluir grupo',
    'view_group': 'Pode ver grupo',
}


def traduzir_permissoes_auth_simples(apps, schema_editor):
    """Atualiza nome das permissões de User e Group para português."""
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    # content_type.app_label = 'auth', model = 'user' ou 'group'
    for app_label, model in [('auth', 'user'), ('auth', 'group')]:
        try:
            ct = ContentType.objects.get(app_label=app_label, model=model)
        except ContentType.DoesNotExist:
            continue
        for codename, name_pt in AUTH_PERMISSIONS_PT.items():
            if (model == 'user' and codename.endswith('_user')) or (model == 'group' and codename.endswith('_group')):
                Permission.objects.filter(content_type=ct, codename=codename).update(name=name_pt)


def reverter_permissoes_auth(apps, schema_editor):
    """Reverte para os nomes em inglês (padrão Django)."""
    EN = {
        'add_user': 'Can add user',
        'change_user': 'Can change user',
        'delete_user': 'Can delete user',
        'view_user': 'Can view user',
        'add_group': 'Can add group',
        'change_group': 'Can change group',
        'delete_group': 'Can delete group',
        'view_group': 'Can view group',
    }
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    for app_label, model in [('auth', 'user'), ('auth', 'group')]:
        try:
            ct = ContentType.objects.get(app_label=app_label, model=model)
        except ContentType.DoesNotExist:
            continue
        for codename, name_en in EN.items():
            if (model == 'user' and codename.endswith('_user')) or (model == 'group' and codename.endswith('_group')):
                Permission.objects.filter(content_type=ct, codename=codename).update(name=name_en)


class Migration(migrations.Migration):

    dependencies = [
        ('relatorios', '0004_add_permission_pode_ver_power_bi'),
    ]

    operations = [
        migrations.RunPython(traduzir_permissoes_auth_simples, reverter_permissoes_auth),
    ]
