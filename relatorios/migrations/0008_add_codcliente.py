# -*- coding: utf-8 -*-
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('relatorios', '0007_recursos_pbi_iniciais'),
    ]

    operations = [
        migrations.AddField(
            model_name='stgvendas',
            name='codcliente',
            field=models.CharField(blank=True, db_index=True, max_length=40, verbose_name='Código cliente'),
        ),
    ]
