from decimal import Decimal
from django.db import models
from django.conf import settings


class UserScope(models.Model):
    """Escopo de acesso: filiais e supervisores permitidos por usuário."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='scope'
    )
    # Lista de códigos de filial permitidos (vazio = todas, se tiver permissão)
    filiais_permitidas = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de CODFILIAL permitidos. Vazio com permissão "todas filiais" = todas.'
    )
    supervisores_permitidos = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de códigos/nomes de supervisor permitidos. Vazio = todos.'
    )

    class Meta:
        verbose_name = 'Escopo do usuário'
        verbose_name_plural = 'Escopos dos usuários'

    def __str__(self):
        return f'Escopo de {self.user.username}'


class StgVendas(models.Model):
    """Tabela staging de vendas importada do CSV."""
    # Identificação
    numnota = models.CharField(max_length=20, db_index=True, blank=True)  # string para não perder zeros
    numped = models.CharField(max_length=24, blank=True, db_index=True)   # 1,72E+09 como string

    # Valores
    valortotal = models.DecimalField(max_digits=16, decimal_places=4, default=Decimal('0'))
    valor_liquido = models.DecimalField(max_digits=16, decimal_places=4, default=Decimal('0'), null=True, blank=True)
    qtd = models.DecimalField(max_digits=16, decimal_places=4, default=Decimal('0'))
    peso = models.DecimalField(max_digits=16, decimal_places=6, default=Decimal('0'), null=True, blank=True)
    pesoliq = models.DecimalField(max_digits=16, decimal_places=6, default=Decimal('0'), null=True, blank=True)

    # Devolução e bonificação
    qtdevol = models.DecimalField(max_digits=16, decimal_places=4, default=Decimal('0'), null=True, blank=True)
    vldevolucao = models.DecimalField(max_digits=16, decimal_places=4, default=Decimal('0'), null=True, blank=True)
    valorbonificado = models.DecimalField(max_digits=16, decimal_places=4, default=Decimal('0'), null=True, blank=True)

    # Preço
    ptabela = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)

    # Data e tempo
    data_faturamento = models.DateTimeField(null=True, blank=True, db_index=True)

    # Filial e equipe
    codfilial = models.CharField(max_length=20, db_index=True, blank=True)
    supervisor = models.CharField(max_length=120, blank=True, db_index=True)
    nomerca = models.CharField(max_length=120, blank=True)

    # Produto e cliente
    produto = models.CharField(max_length=120, blank=True, db_index=True)
    fornecedor = models.CharField(max_length=120, blank=True, db_index=True)
    secao = models.CharField(max_length=120, blank=True, db_index=True)
    categoria = models.CharField(max_length=120, blank=True, db_index=True)
    subcategoria = models.CharField(max_length=120, blank=True)
    cliente = models.CharField(max_length=120, blank=True, db_index=True)

    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Staging Venda'
        verbose_name_plural = 'Staging Vendas'
        permissions = [
            ('pode_ver_relatorio_vendas', 'Pode ver relatório de vendas'),
            ('pode_exportar_excel', 'Pode exportar Excel'),
            ('pode_ver_todas_filiais', 'Pode ver todas as filiais'),
        ]
        indexes = [
            models.Index(fields=['data_faturamento', 'codfilial']),
            models.Index(fields=['data_faturamento', 'supervisor']),
        ]

    def __str__(self):
        return f'{self.numnota} - {self.data_faturamento}'
