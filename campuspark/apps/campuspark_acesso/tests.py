from datetime import datetime, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from apps.campuspark_usuario.models import Aluno, Operador, TipoOperador
from apps.campuspark_veiculo.models import Veiculo
from .historico import formatar_permanencia
from .models import (
    AberturaCancela, ConfiguracaoEstacionamento, RegistroAcesso, StatusAcesso, TipoAbertura, SentidoAbertura,
)
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


def criar_registro(veiculo, entrada, status=StatusAcesso.FINALIZADO, horas=2):
    registro = RegistroAcesso.objects.create(veiculo=veiculo, status=status)
    saida = entrada + timedelta(hours=horas) if status == StatusAcesso.FINALIZADO else None
    # data_entrada é auto_now_add: ajusta direto no banco para simular datas passadas.
    RegistroAcesso.objects.filter(pk=registro.pk).update(data_entrada=entrada, data_saida=saida)
    return registro


class HistoricoAcessosViewTest(TestCase):
    """Histórico completo do operador com filtros e exportação (RF10, RF12)."""

    def setUp(self):
        self.ana = Aluno.objects.create(
            matricula="1111111", cpf="11111111111", nome_completo="Ana Souza",
            email_institucional="ana@catolicasc.org", senha_hash="x",
        )
        self.bruno = Aluno.objects.create(
            matricula="2222222", cpf="22222222222", nome_completo="=Bruno Lima",
            email_institucional="bruno@catolicasc.org", senha_hash="x",
        )
        self.carro = Veiculo.objects.create(aluno=self.ana, placa="AAA1A11", tipo="carro")
        self.moto = Veiculo.objects.create(aluno=self.bruno, placa="BBB2B22", tipo="moto")
        tz = timezone.get_current_timezone()
        criar_registro(self.carro, datetime(2026, 9, 10, 8, 0, tzinfo=tz))
        criar_registro(self.moto, datetime(2026, 10, 5, 9, 0, tzinfo=tz))
        criar_registro(self.carro, datetime(2026, 10, 20, 7, 30, tzinfo=tz), status=StatusAcesso.DENTRO)

        tipo = TipoOperador.objects.create(descricao="Porteiro")
        operador = Operador.objects.create(
            tipo_operador=tipo, cpf="33333333333", nome_completo="Porteiro Teste",
            email="porteiro@catolicasc.org", senha_hash="x",
        )
        session = self.client.session
        session["operador_id"] = operador.id
        session.save()
        self.url = reverse("historico-acessos")

    def placas(self, resp):
        return [r.veiculo.placa for r in resp.context["pagina"]]

    def test_exige_login_de_operador(self):
        self.client.cookies.clear()
        resp = self.client.get(self.url)
        self.assertRedirects(resp, reverse("operador-login"))

    def test_sem_filtros_lista_tudo_do_mais_recente(self):
        resp = self.client.get(self.url)
        self.assertEqual(self.placas(resp), ["AAA1A11", "BBB2B22", "AAA1A11"])

    def test_filtra_por_periodo(self):
        resp = self.client.get(self.url, {"data_inicio": "2026-10-01", "data_fim": "2026-10-10"})
        self.assertEqual(self.placas(resp), ["BBB2B22"])

    def test_filtra_por_busca_status_e_tipo(self):
        resp = self.client.get(self.url, {"busca": "ana"})
        self.assertEqual(self.placas(resp), ["AAA1A11", "AAA1A11"])
        resp = self.client.get(self.url, {"status": StatusAcesso.DENTRO})
        self.assertEqual(self.placas(resp), ["AAA1A11"])
        resp = self.client.get(self.url, {"tipo": "moto"})
        self.assertEqual(self.placas(resp), ["BBB2B22"])

    def test_periodo_invertido_mostra_erro_e_ignora_datas(self):
        resp = self.client.get(self.url, {"data_inicio": "2026-10-10", "data_fim": "2026-10-01"})
        self.assertContains(resp, "A data inicial não pode ser depois da data final.")
        self.assertEqual(len(self.placas(resp)), 3)

    def test_data_invalida_mostra_erro(self):
        resp = self.client.get(self.url, {"data_inicio": "10/10/2026"})
        self.assertContains(resp, "Data inválida")

    def test_exporta_csv_com_os_mesmos_filtros(self):
        resp = self.client.get(reverse("historico-exportar"), {"tipo": "moto"})
        self.assertEqual(resp["Content-Type"], "text/csv; charset=utf-8-sig")
        self.assertIn("attachment;", resp["Content-Disposition"])
        linhas = resp.content.decode("utf-8-sig").strip().splitlines()
        self.assertEqual(linhas[0], "Aluno;Matrícula;Placa;Tipo;Entrada;Saída;Permanência;Status;Operador")
        self.assertEqual(len(linhas), 2)
        self.assertIn("BBB2B22", linhas[1])
        self.assertIn("2h 00min", linhas[1])

    def test_csv_neutraliza_formula_no_nome(self):
        resp = self.client.get(reverse("historico-exportar"), {"busca": "bruno"})
        linha = resp.content.decode("utf-8-sig").strip().splitlines()[1]
        self.assertTrue(linha.startswith("'=Bruno Lima;"))

    def test_formatar_permanencia(self):
        self.assertEqual(formatar_permanencia(timedelta(minutes=45)), "45min")
        self.assertEqual(formatar_permanencia(timedelta(hours=3, minutes=5)), "3h 05min")
        self.assertEqual(formatar_permanencia(timedelta(days=1, hours=2)), "1d 2h 00min")
