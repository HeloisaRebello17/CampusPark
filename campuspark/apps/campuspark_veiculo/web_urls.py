# web_urls.py
# Rotas server-rendered (telas), separadas das rotas de API em urls.py.
from django.urls import path
from .views import ListaVeiculosView, AutorizacaoVeiculoView, EditarVeiculoView, ExcluirVeiculoView

urlpatterns = [
    path("veiculos/", ListaVeiculosView.as_view(), name="lista-veiculos"),
    path("veiculos/<int:veiculo_id>/autorizacao/", AutorizacaoVeiculoView.as_view(), name="veiculo-autorizacao"),
    path("veiculos/<int:veiculo_id>/editar/", EditarVeiculoView.as_view(), name="editar-veiculo"),
    path("veiculos/<int:veiculo_id>/excluir/", ExcluirVeiculoView.as_view(), name="excluir-veiculo"),
]
