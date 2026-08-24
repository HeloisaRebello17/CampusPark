# controllers.py
# Contém a lógica de negócio para cadastro e login de usuários.
from .models import Aluno

def cadastrar_aluno(dados):
    # Cria um novo aluno no banco
    return Aluno.objects.create(**dados)
