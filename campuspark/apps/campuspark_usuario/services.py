# services.py
# Serviços de cadastro e autenticação de Aluno e Operador.
from django.contrib.auth.hashers import make_password, check_password
from .models import Aluno, Operador

class UsuarioService:

    @staticmethod
    def cadastrar_aluno(dados: dict) -> Aluno:
        dados["senha_hash"] = make_password(dados.pop("senha"))
        return Aluno.objects.create(**dados)

    @staticmethod
    def autenticar(matricula: str, senha: str) -> Aluno | None:
        try:
            aluno = Aluno.objects.get(matricula=matricula, ativo=True)
        except Aluno.DoesNotExist:
            return None
        return aluno if check_password(senha, aluno.senha_hash) else None


class OperadorService:

    @staticmethod
    def cadastrar_operador(dados: dict) -> Operador:
        dados["senha_hash"] = make_password(dados.pop("senha"))
        return Operador.objects.create(**dados)

    @staticmethod
    def autenticar(email: str, senha: str) -> Operador | None:
        try:
            operador = Operador.objects.get(email=email, ativo=True)
        except Operador.DoesNotExist:
            return None
        return operador if check_password(senha, operador.senha_hash) else None