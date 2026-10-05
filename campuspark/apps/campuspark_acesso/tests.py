from django.test import TestCase
from apps.campuspark_usuario.models import Aluno, Operador, TipoOperador
from apps.campuspark_veiculo.models import Veiculo
from .models import AberturaCancela, ConfiguracaoEstacionamento, TipoAbertura, SentidoAbertura
from .services import AcessoService, AcessoNegado


def liberar_vagas():
    """A capacidade padrão é 0 vagas, o que nega toda entrada. Nos testes liberamos 1 vaga de carro."""
    ConfiguracaoEstacionamento.objects.update_or_create(
        pk=1, defaults={"vagas_carro": 1, "vagas_moto": 1}
    )


class AcessoServiceTest(TestCase):
    def setUp(self):
        liberar_vagas()
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


class AberturaCancelaTest(TestCase):
    def setUp(self):
        liberar_vagas()
        aluno = Aluno.objects.create(
            matricula="7654321", cpf="22222222222", nome_completo="Aluna Cancela",
            email_institucional="cancela@catolicasc.org", senha_hash="x",
        )
        self.veiculo = Veiculo.objects.create(
            aluno=aluno, placa="XYZ9876", tipo="carro", tag_rfid="TAG2"
        )
        tipo = TipoOperador.objects.create(descricao="Porteiro")
        self.operador = Operador.objects.create(
            tipo_operador=tipo, cpf="33333333333", nome_completo="Porteiro Teste",
            email="porteiro@catolicasc.org", senha_hash="x",
        )

    def test_entrada_automatica_registra_abertura(self):
        registro = AcessoService.validar_entrada("TAG2")
        abertura = AberturaCancela.objects.get()
        self.assertEqual(abertura.tipo, TipoAbertura.AUTOMATICA)
        self.assertEqual(abertura.sentido, SentidoAbertura.ENTRADA)
        self.assertEqual(abertura.registro_id, registro.id)
        self.assertEqual(abertura.veiculo_id, self.veiculo.id)

    def test_saida_automatica_registra_abertura(self):
        AcessoService.validar_entrada("TAG2")
        AcessoService.registrar_saida("TAG2")
        self.assertEqual(AberturaCancela.objects.filter(sentido=SentidoAbertura.SAIDA).count(), 1)

    def test_entrada_negada_nao_abre_cancela(self):
        with self.assertRaises(AcessoNegado):
            AcessoService.validar_entrada("TAG-INEXISTENTE")
        self.assertEqual(AberturaCancela.objects.count(), 0)

    def test_manual_exige_motivo(self):
        with self.assertRaises(AcessoNegado):
            AcessoService.liberar_manual(self.operador, SentidoAbertura.ENTRADA, "   ")
        self.assertEqual(AberturaCancela.objects.count(), 0)

    def test_manual_exige_operador(self):
        with self.assertRaises(AcessoNegado):
            AcessoService.liberar_manual(None, SentidoAbertura.ENTRADA, "Visitante autorizado")

    def test_manual_registra_operador_e_motivo(self):
        abertura = AcessoService.liberar_manual(
            self.operador, SentidoAbertura.SAIDA, "TAG danificada", "xyz9876"
        )
        self.assertEqual(abertura.tipo, TipoAbertura.MANUAL)
        self.assertEqual(abertura.operador_id, self.operador.id)
        self.assertEqual(abertura.motivo, "TAG danificada")
        self.assertEqual(abertura.veiculo_id, self.veiculo.id)
        self.assertEqual(abertura.placa_informada, "XYZ9876")
