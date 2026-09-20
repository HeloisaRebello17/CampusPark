# web_urls.py
# Rotas server-rendered (telas), separadas das rotas de API em urls.py.
from django.urls import path
from .views import OperadorLoginView, OperadorLogoutView, ListaAlunosView, EditarAlunoView

urlpatterns = [
    path("login/", OperadorLoginView.as_view(), name="operador-login"),
    path("logout/", OperadorLogoutView.as_view(), name="operador-logout"),
    path("alunos/", ListaAlunosView.as_view(), name="lista-alunos"),
    path("alunos/<int:aluno_id>/editar/", EditarAlunoView.as_view(), name="editar-aluno"),
]
