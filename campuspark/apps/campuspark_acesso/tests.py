from django.test import TestCase
from apps.campuspark_usuario.models import Aluno
from apps.campuspark_veiculo.models import Veiculo
from .services import AcessoService, AcessoNegado

class AcessoServiceTest(TestCase):
    def setUp(self):
        aluno = Aluno.objects.create(
            matricula="1234567", cpf="11111111111", nome_completo="Teste",
            email_institucional="teste@catolicasc.org", senha_hash="x",
        )
        self.veiculo = Veiculo.objects.create(
            aluno=aluno, placa="ABC1234", tipo="carro", tag_rfid="TAG1"
        )

    def test_entrada_e_saida(self):
        registro = AcessoService.validar_entrada("TAG1")
        self.assertEqual(registro.status, "DENTRO")

        with self.assertRaises(AcessoNegado):
            AcessoService.validar_entrada("TAG1")  # RN05

        registro = AcessoService.registrar_saida("TAG1")
        self.assertEqual(registro.status, "FINALIZADO")

        with self.assertRaises(AcessoNegado):
            AcessoService.registrar_saida("TAG1")  # RN06