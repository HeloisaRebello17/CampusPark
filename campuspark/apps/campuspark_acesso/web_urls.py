# web_urls.py
# Rotas server-rendered (telas), separadas das rotas de API em urls.py.
from django.urls import path
from .views import DashboardView, AtualizarVagasView

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("vagas/atualizar/", AtualizarVagasView.as_view(), name="dashboard-vagas"),
]
