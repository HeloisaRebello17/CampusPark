# routes.py
# Define as rotas específicas para usuários (login, cadastro).
from django.urls import path
from . import controllers

urlpatterns = [
    path("cadastro/", controllers.cadastrar_aluno, name="cadastro_aluno"),
]
