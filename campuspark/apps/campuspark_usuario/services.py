# services.py
# Serviços de validação de acesso usando RFID e reconhecimento facial.
from integrations.rfid_reader import ler_tag
from integrations.facial_recognition import validar_rosto

def validar_entrada(tag):
    # Valida entrada apenas com RFID
    return ler_tag(tag)

def validar_saida(tag, imagem):
    # Valida saída com RFID + facial
    return ler_tag(tag) and validar_rosto(imagem)

from django.contrib.auth.hashers import make_password, check_password
from .models import Aluno

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