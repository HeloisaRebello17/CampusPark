from django.test import TestCase
from .models import Aluno

class AlunoModelTest(TestCase):
    def test_matricula_unica(self):
        Aluno.objects.create(
            matricula="1234567", cpf="11111111111",
            nome_completo="Teste", email_institucional="teste@catolicasc.org",
            senha_hash="x",
        )
        with self.assertRaises(Exception):
            Aluno.objects.create(
                matricula="1234567", cpf="22222222222",
                nome_completo="Outro", email_institucional="outro@catolicasc.org",
                senha_hash="y",
            )