# web_urls.py
# Rotas server-rendered (telas), separadas das rotas de API em urls.py.
from django.urls import path
from .views import (
    DashboardView, AtualizarVagasView, CancelaView, HistoricoAcessosView, ExportarHistoricoView,
)

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("vagas/atualizar/", AtualizarVagasView.as_view(), name="dashboard-vagas"),
    path("cancela/", CancelaView.as_view(), name="cancela"),
    path("historico/", HistoricoAcessosView.as_view(), name="historico-acessos"),
    path("historico/exportar/", ExportarHistoricoView.as_view(), name="historico-exportar"),
]
