from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashWidget
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from .models import UserScope, StgVendas, RecursoPBI


class SenhaResumidaWidget(ReadOnlyPasswordHashWidget):
    """Mostra apenas que a senha está definida, sem exibir algoritmo/salt/hash."""
    def render(self, name, value, attrs, renderer=None):
        if not value:
            return mark_safe('<p class="errornote">Sem senha definida.</p>')
        return mark_safe(
            '<p style="margin:0; color:#888;">Senha definida (não é possível visualizá-la).</p>'
        )


@admin.register(RecursoPBI)
class RecursoPBIAdmin(admin.ModelAdmin):
    list_display = ('nome', 'descricao', 'url_curta', 'link_ver_usuarios')
    ordering = ('ordem', 'nome')
    filter_horizontal = ('usuarios_permitidos',)
    search_fields = ('nome', 'descricao')
    actions = ['excluir_do_sistema']
    add_form_template = 'admin/relatorios/recursopbi/add_form_com_link_visao.html'

    def get_urls(self):
        urls = super().get_urls()
        extra = [
            path('<path:object_id>/usuarios/', self.admin_site.admin_view(self.ver_usuarios_view), name='relatorios_recursopbi_usuarios'),
        ]
        return extra + urls

    def ver_usuarios_view(self, request, object_id):
        """Lista quem acessa o link, ordem de exibição, filtro de usuários e form para alterar ordem."""
        obj = self.get_object(request, object_id)
        if obj is None:
            return redirect('admin:relatorios_recursopbi_changelist')

        # POST: atualizar ordem de exibição
        if request.method == 'POST' and 'ordem' in request.POST:
            try:
                obj.ordem = int(request.POST.get('ordem', 0))
                obj.save(update_fields=['ordem'])
                self.message_user(request, 'Ordem de exibição atualizada.')
            except (ValueError, TypeError):
                pass
            return HttpResponseRedirect(request.path + ('?' + request.GET.urlencode() if request.GET else ''))

        # Lista de usuários com acesso (filtro por nome)
        q = (request.GET.get('q') or '').strip()
        queryset = obj.usuarios_permitidos.all().order_by('username')
        if q:
            queryset = queryset.filter(username__icontains=q)
        usuarios = list(queryset)

        changelist_url = reverse('admin:relatorios_recursopbi_changelist')
        edit_url = reverse('admin:relatorios_recursopbi_change', args=[obj.pk])
        context = {
            **self.admin_site.each_context(request),
            'title': f'Ver quem acessa — «{obj.nome}»',
            'opts': self.model._meta,
            'recurso': obj,
            'usuarios': usuarios,
            'filtro_q': q,
            'changelist_url': changelist_url,
            'edit_url': edit_url,
        }
        return render(request, 'admin/relatorios/recursopbi/ver_usuarios.html', context)

    def response_post_save_add(self, request, obj):
        """Após criar um link, redirecionar para a lista (visão geral) em vez de ficar no formulário."""
        self.message_user(request, f'Link «{obj.nome}» criado. Abaixo a lista de todos os links.')
        return HttpResponseRedirect(reverse('admin:relatorios_recursopbi_changelist'))

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['visao_geral_url'] = reverse('admin:relatorios_recursopbi_changelist')
        return super().add_view(request, form_url=form_url, extra_context=extra_context)

    def link_ver_usuarios(self, obj):
        if not obj or not obj.pk:
            return '—'
        # URL fixa: /admin/relatorios/recursopbi/<pk>/usuarios/ (evita erro de reverse com nome custom)
        base = reverse('admin:relatorios_recursopbi_changelist')
        url = base.rstrip('/') + '/' + str(obj.pk) + '/usuarios/'
        return mark_safe(f'<a href="{url}">Ver quem acessa</a>')
    link_ver_usuarios.short_description = 'Ver quem acessa'

    @admin.action(description='Excluir do sistema (apagar os links selecionados)')
    def excluir_do_sistema(self, request, queryset):
        n = queryset.count()
        queryset.delete()
        self.message_user(request, f'{n} recurso(s) PBI excluído(s) do sistema.')

    def url_curta(self, obj):
        return (obj.url[:50] + '...') if obj.url and len(obj.url) > 50 else (obj.url or '')
    url_curta.short_description = 'URL'

    def usuarios_com_acesso(self, obj):
        usernames = list(obj.usuarios_permitidos.values_list('username', flat=True))
        if not usernames:
            return mark_safe('<span style="color:#94a3b8;">Só staff/admin</span>')
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


# Form: só ajuste da senha (texto e widget resumido)
class CustomUserChangeForm(BaseUserAdmin.form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'password' in self.fields:
            self.fields['password'].widget = SenhaResumidaWidget()
            self.fields['password'].help_text = mark_safe(
                '<a href="../password/">Alterar senha deste usuário</a> (abre a tela de alteração de senha no admin).'
            )


# UserAdmin customizado: lista com coluna Recursos PBI; ao editar, secção separada só para Links PBI
class CustomUserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    list_display = (*BaseUserAdmin.list_display, 'recursos_pbi_na_lista')
    readonly_fields = ['links_pbi_acesso']
    actions = ['remover_acesso_links_pbi']

    # Cadastro (Adicionar usuário): nome, sobrenome, usuário, email, senha e confirmar senha
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'first_name',
                'last_name',
                'username',
                'email',
                'password1',
                'password2',
            ),
        }),
    )

    @admin.action(description='Remover acesso a links PBI')
    def remover_acesso_links_pbi(self, request, queryset):
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        ids = ','.join(str(u.pk) for u in queryset)
        url = reverse('admin_remover_links_pbi') + '?ids=' + ids
        return HttpResponseRedirect(url)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj is not None:
            fieldsets = list(fieldsets) + [
                ('Links PBI (páginas de acesso)', {
                    'fields': ('links_pbi_acesso',),
                    'description': 'Links do Dashboard PBI que este usuário pode acessar. Para adicionar ou remover, use o link abaixo.',
                    'classes': ('wide',),
                }),
            ]
        return fieldsets

    def links_pbi_acesso(self, obj):
        if not obj or not obj.pk:
            return '—'
        try:
            nomes = list(obj.recursos_pbi.values_list('nome', flat=True))
            if not nomes:
                return mark_safe(
                    '<p>Nenhum link atribuído.</p>'
                    '<p><a href="/admin/relatorios/recursopbi/">Gerir em Recursos PBI (links)</a> → edite cada link e adicione este usuário em «Usuários com acesso».</p>'
                )
            from django.urls import reverse
            url = reverse('admin:relatorios_recursopbi_changelist')
            return mark_safe(
                '<p><strong>Com acesso a:</strong> ' + ', '.join(nomes) + '</p>'
                '<p><a href="%s">Adicionar ou remover links em Recursos PBI (links)</a></p>' % url
            )
        except Exception:
            return '—'
    links_pbi_acesso.short_description = 'Links que este usuário acessa'

    def recursos_pbi_na_lista(self, obj):
        if not obj.pk:
            return '—'
        try:
            nomes = list(obj.recursos_pbi.values_list('nome', flat=True))
            if not nomes:
                return '—'
            return ', '.join(nomes[:4]) + (f' (+{len(nomes)-4})' if len(nomes) > 4 else '')
        except Exception:
            return '—'
    recursos_pbi_na_lista.short_description = 'Recursos PBI'


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
