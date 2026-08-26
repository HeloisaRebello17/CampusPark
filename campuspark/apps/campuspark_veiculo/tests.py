from django.test import TestCase
from apps.campuspark_usuario.models import Aluno
from .models import Veiculo

class VeiculoModelTest(TestCase):
    def setUp(self):
        self.aluno = Aluno.objects.create(
            matricula="1234567", cpf="11111111111", nome_completo="Teste",
            email_institucional="teste@catolicasc.org", senha_hash="x",
        )

    def test_placa_unica(self):
        Veiculo.objects.create(aluno=self.aluno, placa="ABC1234", tipo="carro", tag_rfid="TAG1")
        with self.assertRaises(Exception):
            Veiculo.objects.create(aluno=self.aluno, placa="ABC1234", tipo="carro", tag_rfid="TAG2")