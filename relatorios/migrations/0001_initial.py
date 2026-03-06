# Generated manually for MVP Relatórios

from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserScope',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filiais_permitidas', models.JSONField(blank=True, default=list, help_text='Lista de CODFILIAL permitidos. Vazio com permissão "todas filiais" = todas.')),
                ('supervisores_permitidos', models.JSONField(blank=True, default=list, help_text='Lista de códigos/nomes de supervisor permitidos. Vazio = todos.')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='scope', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Escopo do usuário',
                'verbose_name_plural': 'Escopos dos usuários',
            },
        ),
        migrations.CreateModel(
            name='StgVendas',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numnota', models.CharField(blank=True, db_index=True, max_length=20)),
                ('numped', models.CharField(blank=True, db_index=True, max_length=24)),
                ('valortotal', models.DecimalField(decimal_places=4, default=Decimal('0'), max_digits=16)),
                ('valor_liquido', models.DecimalField(blank=True, decimal_places=4, max_digits=16, null=True)),
                ('qtd', models.DecimalField(decimal_places=4, default=Decimal('0'), max_digits=16)),
                ('peso', models.DecimalField(blank=True, decimal_places=6, max_digits=16, null=True)),
                ('pesoliq', models.DecimalField(blank=True, decimal_places=6, max_digits=16, null=True)),
                ('qtdevol', models.DecimalField(blank=True, decimal_places=4, max_digits=16, null=True)),
                ('vldevolucao', models.DecimalField(blank=True, decimal_places=4, max_digits=16, null=True)),
                ('valorbonificado', models.DecimalField(blank=True, decimal_places=4, max_digits=16, null=True)),
                ('ptabela', models.DecimalField(blank=True, decimal_places=4, max_digits=16, null=True)),
                ('data_faturamento', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('codfilial', models.CharField(blank=True, db_index=True, max_length=20)),
                ('supervisor', models.CharField(blank=True, db_index=True, max_length=120)),
                ('nomerca', models.CharField(blank=True, max_length=120)),
                ('produto', models.CharField(blank=True, db_index=True, max_length=120)),
                ('secao', models.CharField(blank=True, db_index=True, max_length=120)),
                ('categoria', models.CharField(blank=True, db_index=True, max_length=120)),
                ('subcategoria', models.CharField(blank=True, max_length=120)),
                ('cliente', models.CharField(blank=True, db_index=True, max_length=120)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Staging Venda',
                'verbose_name_plural': 'Staging Vendas',
                'permissions': [
                    ('pode_ver_relatorio_vendas', 'Pode ver relatório de vendas'),
                    ('pode_exportar_excel', 'Pode exportar Excel'),
                    ('pode_ver_todas_filiais', 'Pode ver todas as filiais'),
                ],
            },
        ),
        migrations.AddIndex(
            model_name='stgvendas',
            index=models.Index(fields=['data_faturamento', 'codfilial'], name='relatorios_data_fa_idx'),
        ),
        migrations.AddIndex(
            model_name='stgvendas',
            index=models.Index(fields=['data_faturamento', 'supervisor'], name='relatorios_data_fa_supervi_idx'),
        ),
    ]
