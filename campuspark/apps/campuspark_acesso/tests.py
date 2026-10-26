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


class SaidaPelaFaceTest(TestCase):
    def setUp(self):
        liberar_vagas()
        self.aluno = Aluno.objects.create(
            matricula="1111111", cpf="44444444444", nome_completo="Dono do Carro",
            email_institucional="dono@catolicasc.org", senha_hash="x",
        )
        self.outro_aluno = Aluno.objects.create(
            matricula="2222222", cpf="55555555555", nome_completo="Outro Aluno",
            email_institucional="outro@catolicasc.org", senha_hash="x",
        )
        Veiculo.objects.create(aluno=self.aluno, placa="FAC1234", tipo="carro", tag_rfid="TAG3")
        AcessoService.validar_entrada("TAG3", aluno_reconhecido=self.aluno)

    def ativar_modulo(self, ativo=True):
        ConfiguracaoEstacionamento.objects.filter(pk=1).update(exigir_face_saida=ativo)

    def test_modulo_desativado_libera_saida_so_com_tag(self):
        registro = AcessoService.registrar_saida("TAG3")
        self.assertEqual(registro.status, "FINALIZADO")

    def test_modulo_ativo_exige_rosto(self):
        self.ativar_modulo()
        with self.assertRaises(AcessoNegado):
            AcessoService.registrar_saida("TAG3")
        self.assertFalse(AberturaCancela.objects.filter(sentido=SentidoAbertura.SAIDA).exists())

    def test_modulo_ativo_libera_com_rosto_do_dono(self):
        self.ativar_modulo()
        registro = AcessoService.registrar_saida("TAG3", aluno_reconhecido=self.aluno)
        self.assertEqual(registro.status, "FINALIZADO")
        self.assertTrue(AberturaCancela.objects.filter(sentido=SentidoAbertura.SAIDA).exists())

    def test_rosto_de_outro_aluno_nega_saida(self):
        for ativo in (True, False):
            self.ativar_modulo(ativo)
            with self.assertRaises(AcessoNegado):
                AcessoService.registrar_saida("TAG3", aluno_reconhecido=self.outro_aluno)
        self.assertFalse(AberturaCancela.objects.filter(sentido=SentidoAbertura.SAIDA).exists())


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

    def test_face_saida_altera_configuracao(self):
        AcessoService.definir_face_saida(self.operador, True)
        self.assertTrue(ConfiguracaoEstacionamento.obter().exigir_face_saida)
        AcessoService.definir_face_saida(self.operador, False)
        self.assertFalse(ConfiguracaoEstacionamento.obter().exigir_face_saida)

    def test_face_saida_exige_operador(self):
        with self.assertRaises(AcessoNegado):
            AcessoService.definir_face_saida(None, True)

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
        self.assertEqual(linhas[0], "Nome;Matrícula;Origem;Documento (visitante);Placa;Tipo;Entrada;Saída;Permanência;Status;Liberação;Motivo;Operador")
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


class EntradaSaidaManualTest(TestCase):
    """Entrada/saída manual pelo operador, para aluno cadastrado ou visitante."""

    def setUp(self):
        liberar_vagas()
        self.aluno = Aluno.objects.create(
            matricula="1234567", cpf="11111111111", nome_completo="Aluna Manual",
            email_institucional="manual@catolicasc.org", senha_hash="x",
        )
        self.veiculo = Veiculo.objects.create(aluno=self.aluno, placa="ABC1D23", tipo="carro", tag_rfid="TAG1")
        tipo = TipoOperador.objects.create(descricao="Porteiro")
        self.operador = Operador.objects.create(
            tipo_operador=tipo, cpf="33333333333", nome_completo="Porteiro Teste",
            email="porteiro@catolicasc.org", senha_hash="x",
        )

    def visitante(self, **overrides):
        dados = {"placa": "vis-1234", "motivo": "Palestrante", "tipo": "carro",
                 "nome": "Carlos Visitante", "documento": "123.456.789-01"}
        dados.update(overrides)
        return AcessoService.entrada_manual(self.operador, **dados)

    def test_entrada_manual_de_cadastrado_cria_registro_e_abertura(self):
        registro, aviso = AcessoService.entrada_manual(self.operador, "abc-1d23", "TAG não leu")
        self.assertEqual(aviso, "")
        self.assertEqual(registro.veiculo, self.veiculo)
        self.assertTrue(registro.liberacao_manual)
        self.assertEqual(registro.operador, self.operador)
        abertura = AberturaCancela.objects.get()
        self.assertEqual(abertura.tipo, TipoAbertura.MANUAL)
        self.assertEqual(abertura.registro, registro)

    def test_cadastrado_que_entrou_manual_sai_pela_tag(self):
        AcessoService.entrada_manual(self.operador, "ABC1D23", "TAG não leu")
        registro = AcessoService.registrar_saida("TAG1")
        self.assertEqual(registro.status, StatusAcesso.FINALIZADO)

    def test_cadastrado_bloqueado_entra_com_aviso(self):
        self.veiculo.autorizado = False
        self.veiculo.save()
        registro, aviso = AcessoService.entrada_manual(self.operador, "ABC1D23", "Regularizando cadastro")
        self.assertIn("bloqueado", aviso)
        self.assertIn("bloqueado/inativo", registro.motivo)

    def test_cadastrado_ja_dentro_nao_entra_de_novo(self):
        AcessoService.validar_entrada("TAG1")
        with self.assertRaises(AcessoNegado):
            AcessoService.entrada_manual(self.operador, "ABC1D23", "Teste")

    def test_visitante_cria_registro_sem_veiculo(self):
        registro, _ = self.visitante()
        self.assertIsNone(registro.veiculo)
        self.assertEqual(registro.placa_visitante, "VIS1234")
        self.assertEqual(registro.documento_visitante, "12345678901")
        self.assertEqual(registro.nome_exibicao, "Carlos Visitante")
        self.assertEqual(registro.status, StatusAcesso.DENTRO)

    def test_visitante_exige_dados(self):
        for campo, valor in [("tipo", ""), ("nome", " "), ("documento", "12"), ("motivo", "")]:
            with self.subTest(campo=campo):
                with self.assertRaises(AcessoNegado):
                    self.visitante(**{campo: valor})
        self.assertFalse(RegistroAcesso.objects.exists())

    def test_placa_invalida(self):
        with self.assertRaises(AcessoNegado):
            self.visitante(placa="12")

    def test_visitante_ocupa_vaga_e_respeita_lotacao(self):
        self.visitante()  # ocupa a única vaga de carro
        with self.assertRaises(AcessoNegado):
            AcessoService.validar_entrada("TAG1")  # aluno não entra: lotado
        with self.assertRaises(AcessoNegado):
            self.visitante(placa="OUT9876")
        self.visitante(placa="MOT1234", tipo="moto")  # moto ainda tem vaga

    def test_visitante_ja_dentro_nao_entra_de_novo(self):
        ConfiguracaoEstacionamento.objects.update(vagas_carro=5)
        self.visitante()
        with self.assertRaises(AcessoNegado):
            self.visitante()

    def test_saida_manual_libera_vaga(self):
        registro, _ = self.visitante()
        AcessoService.saida_manual(self.operador, registro.id)
        registro.refresh_from_db()
        self.assertEqual(registro.status, StatusAcesso.FINALIZADO)
        self.assertIsNotNone(registro.data_saida)
        self.assertEqual(
            AberturaCancela.objects.filter(sentido=SentidoAbertura.SAIDA, registro=registro).count(), 1
        )
        AcessoService.validar_entrada("TAG1")  # vaga voltou a ficar livre

    def test_saida_manual_de_registro_ja_finalizado(self):
        registro, _ = self.visitante()
        AcessoService.saida_manual(self.operador, registro.id)
        with self.assertRaises(AcessoNegado):
            AcessoService.saida_manual(self.operador, registro.id)


class CancelaManualViewTest(TestCase):
    """Tela da cancela: consulta de placa, entrada e saída manual."""

    def setUp(self):
        liberar_vagas()
        aluno = Aluno.objects.create(
            matricula="1234567", cpf="11111111111", nome_completo="Aluna Tela",
            email_institucional="tela@catolicasc.org", senha_hash="x",
        )
        Veiculo.objects.create(aluno=aluno, placa="ABC1D23", tipo="carro", autorizado=False)
        tipo = TipoOperador.objects.create(descricao="Porteiro")
        operador = Operador.objects.create(
            tipo_operador=tipo, cpf="33333333333", nome_completo="Porteiro Teste",
            email="porteiro@catolicasc.org", senha_hash="x",
        )
        session = self.client.session
        session["operador_id"] = operador.id
        session.save()
        self.url = reverse("cancela")

    def test_consulta_placa_cadastrada_mostra_aluno_e_alerta_bloqueio(self):
        resp = self.client.get(self.url, {"placa": "abc1d23"})
        self.assertContains(resp, "Aluna Tela")
        self.assertContains(resp, "bloqueado")

    def test_consulta_placa_sem_cadastro_pede_dados_do_visitante(self):
        resp = self.client.get(self.url, {"placa": "XYZ9876"})
        self.assertContains(resp, "sem cadastro")
        self.assertContains(resp, 'name="documento"')

    def test_entrada_e_saida_de_visitante_pela_tela(self):
        resp = self.client.post(self.url, {
            "acao": "entrada_manual", "placa": "XYZ9876", "tipo": "carro",
            "nome": "Visitante Tela", "documento": "1234567", "motivo": "Entrega",
        })
        self.assertContains(resp, "Entrada de XYZ9876 registrada")
        registro = RegistroAcesso.objects.get(placa_visitante="XYZ9876")

        historico = self.client.get(reverse("historico-acessos"), {"origem": "visitante"})
        self.assertContains(historico, "Visitante Tela")

        resp = self.client.post(self.url, {"acao": "saida_manual", "registro_id": registro.id})
        self.assertContains(resp, "Saída de XYZ9876 registrada")
        registro.refresh_from_db()
        self.assertEqual(registro.status, StatusAcesso.FINALIZADO)

    def test_entrada_de_visitante_com_dados_faltando_mantem_formulario(self):
        resp = self.client.post(self.url, {
            "acao": "entrada_manual", "placa": "XYZ9876", "tipo": "carro",
            "nome": "Visitante Tela", "documento": "", "motivo": "Entrega",
        })
        self.assertContains(resp, "Informe o CPF ou RG", status_code=400)
        self.assertContains(resp, 'value="Visitante Tela"', status_code=400)

    def test_saida_manual_com_registro_invalido(self):
        resp = self.client.post(self.url, {"acao": "saida_manual", "registro_id": "abc"})
        self.assertEqual(resp.status_code, 400)

    def test_exportacao_inclui_visitante(self):
        self.client.post(self.url, {
            "acao": "entrada_manual", "placa": "XYZ9876", "tipo": "moto",
            "nome": "Visitante CSV", "documento": "1234567", "motivo": "Entrega",
        })
        csv = self.client.get(reverse("historico-exportar")).content.decode("utf-8-sig")
        linha = csv.strip().splitlines()[1]
        self.assertIn("Visitante CSV;;Visitante;1234567;XYZ9876;Moto", linha)
        self.assertIn("Manual;Entrega", linha)

