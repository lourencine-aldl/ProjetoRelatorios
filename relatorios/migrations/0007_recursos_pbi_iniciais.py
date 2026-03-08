# -*- coding: utf-8 -*-
from django.db import migrations


def criar_recursos_iniciais(apps, schema_editor):
    RecursoPBI = apps.get_model('relatorios', 'RecursoPBI')
    recursos = [
        {
            'nome': 'Diretoria',
            'descricao': 'Dados da Diretoria',
            'url': 'https://app.powerbi.com/view?r=eyJrIjoiZThlOWEyOTUtZGNiZi00ZDc2LThkODItMDIwOTQ0ODA0MDhlIiwidCI6IjM5YmY5MWE0LWFjYmYtNDY1Ni1iNzkwLTRmNjQ1N2M2MTkzYyJ9',
            'ordem': 10,
        },
        {
            'nome': 'Gestão de Vendas',
            'descricao': 'Dashboard de gestão de vendas',
            'url': 'https://app.powerbi.com/view?r=eyJrIjoiZmFlMzMyOGUtZTUxYy00MGIxLTk3OTItMmQyZDgxZjUxMDRiIiwidCI6IjM5YmY5MWE0LWFjYmYtNDY1Ni1iNzkwLTRmNjQ1N2M2MTkzYyJ9',
            'ordem': 20,
        },
        {
            'nome': 'Gestão de Preços',
            'descricao': 'Dashboard de gestão de preços',
            'url': 'https://app.powerbi.com/view?r=eyJrIjoiNjcyODE5MzgtYjliNy00ZGQ5LTg1ZDktNWFkYTc2MTEwMDg0IiwidCI6IjM5YmY5MWE0LWFjYmYtNDY1Ni1iNzkwLTRmNjQ1N2M2MTkzYyJ9',
            'ordem': 30,
        },
    ]
    for r in recursos:
        RecursoPBI.objects.get_or_create(nome=r['nome'], defaults=r)


def reverter(apps, schema_editor):
    RecursoPBI = apps.get_model('relatorios', 'RecursoPBI')
    for nome in ('Diretoria', 'Gestão de Vendas', 'Gestão de Preços'):
        RecursoPBI.objects.filter(nome=nome).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('relatorios', '0006_add_recurso_pbi'),
    ]

    operations = [
        migrations.RunPython(criar_recursos_iniciais, reverter),
    ]
