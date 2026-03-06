from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserScope, StgVendas


@admin.register(UserScope)
class UserScopeAdmin(admin.ModelAdmin):
    list_display = ('user', 'filiais_permitidas', 'supervisores_permitidos')
    search_fields = ('user__username',)
    raw_id_fields = ('user',)


@admin.register(StgVendas)
class StgVendasAdmin(admin.ModelAdmin):
    list_display = ('numnota', 'data_faturamento', 'codfilial', 'supervisor', 'valortotal', 'cliente')
    list_filter = ('codfilial', 'data_faturamento')
    search_fields = ('numnota', 'cliente', 'produto', 'supervisor')
    date_hierarchy = 'data_faturamento'
    readonly_fields = ('created_at',)
