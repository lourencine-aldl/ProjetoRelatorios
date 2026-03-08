from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserScope, StgVendas, RecursoPBI


@admin.register(RecursoPBI)
class RecursoPBIAdmin(admin.ModelAdmin):
    list_display = ('nome', 'descricao', 'ordem', 'url_curta', 'usuarios_com_acesso')
    list_editable = ('ordem',)
    ordering = ('ordem', 'nome')
    filter_horizontal = ('usuarios_permitidos',)
    search_fields = ('nome', 'descricao')

    def url_curta(self, obj):
        return (obj.url[:50] + '...') if obj.url and len(obj.url) > 50 else (obj.url or '')
    url_curta.short_description = 'URL'

    def usuarios_com_acesso(self, obj):
        usernames = list(obj.usuarios_permitidos.values_list('username', flat=True))
        if not usernames:
            return '—'
        if len(usernames) <= 5:
            return ', '.join(usernames)
        return ', '.join(usernames[:5]) + f' (+{len(usernames) - 5})'
    usuarios_com_acesso.short_description = 'Usuários com acesso'


@admin.register(UserScope)
class UserScopeAdmin(admin.ModelAdmin):
    list_display = ('user', 'filiais_permitidas', 'supervisores_permitidos')
    search_fields = ('user__username',)
    raw_id_fields = ('user',)


@admin.register(StgVendas)
class StgVendasAdmin(admin.ModelAdmin):
    list_display = ('numnota', 'data_faturamento', 'codfilial', 'supervisor', 'valortotal', 'valor_liquido', 'cliente')
    list_filter = ('codfilial', 'data_faturamento')
    search_fields = ('numnota', 'cliente', 'produto', 'supervisor')
    date_hierarchy = 'data_faturamento'
    readonly_fields = ('created_at',)


# Form customizado para editar usuário + Recursos PBI (relação reversa)
class CustomUserChangeForm(BaseUserAdmin.form):
    def __init__(self, *args, **kwargs):
        from django import forms
        super().__init__(*args, **kwargs)
        self.fields['recursos_pbi'] = forms.ModelMultipleChoiceField(
            queryset=RecursoPBI.objects.all().order_by('ordem', 'nome'),
            required=False,
            label='Recursos PBI com acesso',
            help_text='Links do Dashboard PBI que este usuário pode acessar.',
            widget=admin.widgets.FilteredSelectMultiple('Recursos PBI', is_stacked=False),
        )
        if self.instance and self.instance.pk:
            self.fields['recursos_pbi'].initial = list(self.instance.recursos_pbi.values_list('pk', flat=True))
        else:
            self.fields['recursos_pbi'].initial = []

    def save(self, commit=True):
        return super().save(commit=commit)


# UserAdmin customizado: ver e editar "Recursos PBI com acesso" por usuário
class CustomUserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    list_display = (*BaseUserAdmin.list_display, 'recursos_pbi_na_lista')
    filter_horizontal = (*BaseUserAdmin.filter_horizontal, 'recursos_pbi')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Recursos PBI', {
            'fields': ('recursos_pbi',),
            'description': 'Links do Dashboard PBI que este usuário pode acessar. Ele também precisa da permissão "Pode ver Dashboard Power BI".',
        }),
    )

    def recursos_pbi_na_lista(self, obj):
        if not obj.pk:
            return '—'
        nomes = list(obj.recursos_pbi.values_list('nome', flat=True))
        if not nomes:
            return '—'
        return ', '.join(nomes[:4]) + (f' (+{len(nomes)-4})' if len(nomes) > 4 else '')
    recursos_pbi_na_lista.short_description = 'Recursos PBI'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if hasattr(form, 'cleaned_data') and 'recursos_pbi' in form.cleaned_data:
            obj.recursos_pbi.set(form.cleaned_data['recursos_pbi'])


# Desregistrar o User padrão e registrar com o nosso (para ver/editar acessos PBI)
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
