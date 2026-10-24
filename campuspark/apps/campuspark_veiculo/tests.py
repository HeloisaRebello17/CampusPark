from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.urls import reverse

from apps.campuspark_acesso.models import RegistroAcesso, StatusAcesso
from apps.campuspark_usuario.models import Aluno, Operador, TipoOperador
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


def criar_aluno(matricula="1234567", cpf="11111111111", email="aluno@catolicasc.org"):
    return Aluno.objects.create(
        matricula=matricula, cpf=cpf, nome_completo="Aluno Teste",
        email_institucional=email, senha_hash=make_password("senha123"),
    )


def criar_operador(descricao="Porteiro", cpf="33333333333"):
    tipo, _ = TipoOperador.objects.get_or_create(descricao=descricao)
    return Operador.objects.create(
        tipo_operador=tipo, cpf=cpf, nome_completo=f"{descricao} Teste",
        email=f"{cpf}@catolicasc.org", senha_hash="x",
    )


class VeiculoAlunoViewTest(TestCase):
    """Edição/exclusão do veículo pelo próprio aluno (usuario/pages.py)."""

    def setUp(self):
        self.aluno = criar_aluno()
        self.veiculo = Veiculo.objects.create(
            aluno=self.aluno, placa="ABC1D23", tipo="carro", modelo="Civic 2020", tag_rfid="TAG1",
        )
        session = self.client.session
        session["aluno_id"] = self.aluno.id
        session.save()

    def dados(self, **overrides):
        dados = {"tipo_veiculo": "motocicleta", "placa": "xyz-9e87", "modelo_ano": "CG 160 2023"}
        dados.update(overrides)
        return dados

    def test_editar_atualiza_dados(self):
        resp = self.client.post(reverse("veiculo-editar", args=[self.veiculo.id]), self.dados(seguro_ativo="on"))
        self.assertRedirects(resp, reverse("meus-veiculos"))
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.placa, "XYZ9E87")
        self.assertEqual(self.veiculo.tipo, "moto")
        self.assertEqual(self.veiculo.modelo, "CG 160 2023")
        self.assertTrue(self.veiculo.seguro_ativo)

    def test_editar_nao_altera_autorizacao(self):
        self.veiculo.autorizado = False
        self.veiculo.save()
        self.client.post(reverse("veiculo-editar", args=[self.veiculo.id]), self.dados(autorizado="on"))
        self.veiculo.refresh_from_db()
        self.assertFalse(self.veiculo.autorizado)

    def test_editar_com_placa_de_outro_veiculo_mostra_erro(self):
        outro = criar_aluno(matricula="7654321", cpf="22222222222", email="outro@catolicasc.org")
        Veiculo.objects.create(aluno=outro, placa="XYZ9E87", tipo="carro")
        resp = self.client.post(reverse("veiculo-editar", args=[self.veiculo.id]), self.dados())
        self.assertContains(resp, "Já existe um veículo cadastrado com essa placa.", status_code=400)

    def test_editar_placa_invalida_mostra_erro(self):
        resp = self.client.post(reverse("veiculo-editar", args=[self.veiculo.id]), self.dados(placa="12"))
        self.assertContains(resp, "Placa inválida", status_code=400)

    def test_nao_edita_veiculo_de_outro_aluno(self):
        outro = criar_aluno(matricula="7654321", cpf="22222222222", email="outro@catolicasc.org")
        veiculo_alheio = Veiculo.objects.create(aluno=outro, placa="QWE1234", tipo="carro")
        resp = self.client.post(reverse("veiculo-editar", args=[veiculo_alheio.id]), self.dados())
        self.assertEqual(resp.status_code, 404)
        resp = self.client.post(reverse("veiculo-excluir", args=[veiculo_alheio.id]))
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Veiculo.objects.filter(pk=veiculo_alheio.id).exists())

    def test_nao_edita_veiculo_dentro_do_estacionamento(self):
        RegistroAcesso.objects.create(veiculo=self.veiculo, status=StatusAcesso.DENTRO)
        resp = self.client.post(reverse("veiculo-editar", args=[self.veiculo.id]), self.dados())
        self.assertRedirects(resp, reverse("meus-veiculos"))
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.placa, "ABC1D23")

    def test_excluir_remove_veiculo_sem_historico(self):
        resp = self.client.post(reverse("veiculo-excluir", args=[self.veiculo.id]))
        self.assertRedirects(resp, reverse("meus-veiculos"))
        self.assertFalse(Veiculo.objects.filter(pk=self.veiculo.id).exists())

    def test_excluir_exige_post(self):
        resp = self.client.get(reverse("veiculo-excluir", args=[self.veiculo.id]))
        self.assertEqual(resp.status_code, 405)
        self.assertTrue(Veiculo.objects.filter(pk=self.veiculo.id).exists())

    def test_excluir_veiculo_com_historico_e_negado(self):
        RegistroAcesso.objects.create(veiculo=self.veiculo, status=StatusAcesso.FINALIZADO)
        resp = self.client.post(reverse("veiculo-excluir", args=[self.veiculo.id]), follow=True)
        self.assertContains(resp, "possui histórico de acessos")
        self.assertTrue(Veiculo.objects.filter(pk=self.veiculo.id).exists())

    def test_excluir_veiculo_dentro_do_estacionamento_e_negado(self):
        RegistroAcesso.objects.create(veiculo=self.veiculo, status=StatusAcesso.DENTRO)
        resp = self.client.post(reverse("veiculo-excluir", args=[self.veiculo.id]), follow=True)
        self.assertContains(resp, "está dentro do estacionamento")
        self.assertTrue(Veiculo.objects.filter(pk=self.veiculo.id).exists())


class VeiculoOperadorViewTest(TestCase):
    """Gestão de veículos pelo operador (veiculo/views.py)."""

    def setUp(self):
        self.aluno = criar_aluno()
        self.veiculo = Veiculo.objects.create(aluno=self.aluno, placa="ABC1D23", tipo="carro", tag_rfid="TAG1")
        self.porteiro = criar_operador("Porteiro", cpf="33333333333")
        self.admin = criar_operador("Administrador", cpf="44444444444")

    def logar(self, operador):
        session = self.client.session
        session["operador_id"] = operador.id
        session.save()

    def test_lista_exige_login_de_operador(self):
        resp = self.client.get(reverse("lista-veiculos"))
        self.assertRedirects(resp, reverse("operador-login"))

    def test_aluno_nao_consegue_alterar_autorizacao(self):
        session = self.client.session
        session["aluno_id"] = self.aluno.id
        session.save()
        resp = self.client.post(reverse("veiculo-autorizacao", args=[self.veiculo.id]), {"autorizado": "0"})
        self.assertRedirects(resp, reverse("operador-login"))
        self.veiculo.refresh_from_db()
        self.assertTrue(self.veiculo.autorizado)

    def test_lista_filtra_por_busca_e_situacao(self):
        outro = criar_aluno(matricula="7654321", cpf="22222222222", email="outro@catolicasc.org")
        Veiculo.objects.create(aluno=outro, placa="QWE1234", tipo="moto", autorizado=False)
        self.logar(self.porteiro)
        resp = self.client.get(reverse("lista-veiculos"), {"autorizacao": "bloqueado"})
        self.assertContains(resp, "QWE1234")
        self.assertNotContains(resp, "ABC1D23")
        resp = self.client.get(reverse("lista-veiculos"), {"busca": "abc1"})
        self.assertContains(resp, "ABC1D23")
        self.assertNotContains(resp, "QWE1234")

    def test_porteiro_bloqueia_e_autoriza(self):
        self.logar(self.porteiro)
        url = reverse("veiculo-autorizacao", args=[self.veiculo.id])
        self.client.post(url, {"autorizado": "0"})
        self.veiculo.refresh_from_db()
        self.assertFalse(self.veiculo.autorizado)
        self.client.post(url, {"autorizado": "1"})
        self.veiculo.refresh_from_db()
        self.assertTrue(self.veiculo.autorizado)

    def test_autorizacao_volta_para_lista_filtrada(self):
        self.logar(self.porteiro)
        destino = reverse("lista-veiculos") + "?autorizacao=autorizado"
        resp = self.client.post(
            reverse("veiculo-autorizacao", args=[self.veiculo.id]), {"autorizado": "0", "next": destino},
        )
        self.assertRedirects(resp, destino)

    def test_autorizacao_ignora_next_externo(self):
        self.logar(self.porteiro)
        resp = self.client.post(
            reverse("veiculo-autorizacao", args=[self.veiculo.id]),
            {"autorizado": "0", "next": "https://site-malicioso.com/"},
        )
        self.assertRedirects(resp, reverse("lista-veiculos"))

    def test_porteiro_nao_edita_nem_exclui(self):
        self.logar(self.porteiro)
        resp = self.client.post(reverse("editar-veiculo", args=[self.veiculo.id]), {"placa": "XYZ1234", "tipo": "carro"})
        self.assertEqual(resp.status_code, 403)
        resp = self.client.post(reverse("excluir-veiculo", args=[self.veiculo.id]))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Veiculo.objects.filter(pk=self.veiculo.id).exists())

    def test_admin_edita_veiculo(self):
        self.logar(self.admin)
        resp = self.client.post(reverse("editar-veiculo", args=[self.veiculo.id]), {
            "placa": "xyz-1234", "tipo": "moto", "fabricante": "Honda", "modelo": "CG 160", "cor": "Preta",
        })
        self.assertRedirects(resp, reverse("lista-veiculos"))
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.placa, "XYZ1234")
        self.assertEqual(self.veiculo.tipo, "moto")
        self.assertEqual(self.veiculo.fabricante, "Honda")
        self.assertFalse(self.veiculo.autorizado)

    def test_admin_edita_com_tipo_invalido_mostra_erro(self):
        self.logar(self.admin)
        resp = self.client.post(reverse("editar-veiculo", args=[self.veiculo.id]), {"placa": "XYZ1234", "tipo": "caminhao"})
        self.assertContains(resp, "Selecione um tipo de veículo válido.", status_code=400)

    def test_admin_exclui_veiculo_sem_historico(self):
        self.logar(self.admin)
        resp = self.client.post(reverse("excluir-veiculo", args=[self.veiculo.id]))
        self.assertRedirects(resp, reverse("lista-veiculos"))
        self.assertFalse(Veiculo.objects.filter(pk=self.veiculo.id).exists())

    def test_admin_nao_edita_veiculo_dentro_do_estacionamento(self):
        RegistroAcesso.objects.create(veiculo=self.veiculo, status=StatusAcesso.DENTRO)
        self.logar(self.admin)
        resp = self.client.get(reverse("editar-veiculo", args=[self.veiculo.id]))
        self.assertRedirects(resp, reverse("lista-veiculos"))
