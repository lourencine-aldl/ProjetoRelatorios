from django.contrib import admin
from django.urls import path, include
from relatorios.views import remover_links_pbi_usuarios_view, gerir_links_usuario_view

urlpatterns = [
    path('admin/remover-links-pbi/', remover_links_pbi_usuarios_view, name='admin_remover_links_pbi'),
    path('admin/gerir-links-usuario/<int:user_id>/', gerir_links_usuario_view, name='admin_gerir_links_usuario'),
    path('admin/', admin.site.urls),
    path('', include('relatorios.urls')),
]
