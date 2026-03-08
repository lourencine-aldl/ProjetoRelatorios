# -*- coding: utf-8 -*-
from django.db import migrations


def create_pbi_permission(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    StgVendas = apps.get_model('relatorios', 'StgVendas')
    ct = ContentType.objects.get_for_model(StgVendas)
    Permission.objects.get_or_create(
        codename='pode_ver_power_bi',
        content_type=ct,
        defaults={'name': 'Pode ver Dashboard Power BI'},
    )


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('relatorios', '0003_add_fornecedor'),
    ]

    operations = [
        migrations.RunPython(create_pbi_permission, reverse_noop),
    ]
