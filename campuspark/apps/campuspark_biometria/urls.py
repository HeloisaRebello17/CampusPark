from django.urls import path
from .views import CadastroFacialView, ReconhecimentoFacialView

urlpatterns = [
    path("cadastro/", CadastroFacialView.as_view(), name="biometria-cadastro"),
    path("reconhecer/", ReconhecimentoFacialView.as_view(), name="biometria-reconhecer"),
]
