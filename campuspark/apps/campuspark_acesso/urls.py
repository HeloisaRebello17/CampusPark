from django.urls import path
from .views import EntradaView, SaidaView

urlpatterns = [
    path("entrada/", EntradaView.as_view(), name="acesso-entrada"),
    path("saida/", SaidaView.as_view(), name="acesso-saida"),
]