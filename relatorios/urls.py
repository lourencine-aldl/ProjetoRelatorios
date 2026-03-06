from django.urls import path
from . import views
from .api import DashboardAPIView

urlpatterns = [
    path('', views.root_redirect),
    path('teste/', views.teste_web_view, name='teste_web'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard-pbi/', views.dashboard_pbi, name='dashboard_pbi'),
    path('relatorio/', views.RelatorioDetalhadoView.as_view(), name='relatorio_detalhado'),
    path('export/excel/', views.export_excel_view, name='export_excel'),
    path('atualizar-dados/', views.atualizar_dados_view, name='atualizar_dados'),
    # API REST (JSON)
    path('api/dashboard/', DashboardAPIView.as_view(), name='api_dashboard'),
]
