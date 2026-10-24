from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.campuspark_usuario.models import Operador, TipoOperador


def criar_operador(descricao, cpf, ativo=True):
    tipo, _ = TipoOperador.objects.get_or_create(descricao=descricao)
    return Operador.objects.create(
        tipo_operador=tipo, cpf=cpf, nome_completo=f"{descricao} Teste",
        email=f"{cpf}@catolicasc.org", senha_hash="x", ativo=ativo,
    )


def logar(client, operador):
    session = client.session
    session["operador_id"] = operador.id
    session.save()


CSRF_TOKEN = "a" * 32


def com_csrf(client):
    """Simula o cookie + header de CSRF que o navegador mandaria a partir de uma tela do sistema."""
    client.cookies[settings.CSRF_COOKIE_NAME] = CSRF_TOKEN
    return {"HTTP_X_CSRFTOKEN": CSRF_TOKEN}


@override_settings(CAMPUSPARK_API_KEY="chave-de-teste")
class PermissoesApiTest(TestCase):
    """A API REST não pode mais ser usada sem login (RNF01, RNF14)."""

    def setUp(self):
        self.porteiro = criar_operador("Porteiro", "33333333333")
        self.admin = criar_operador("Administrador", "44444444444")
        self.client = Client(enforce_csrf_checks=True)
        self.saida = reverse("acesso-saida")

    def test_crud_bloqueado_sem_login(self):
        for url in ("/api/usuario/alunos/", "/api/usuario/operadores/", "/api/veiculo/veiculos/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_crud_bloqueado_para_porteiro(self):
        logar(self.client, self.porteiro)
        self.assertEqual(self.client.get("/api/usuario/alunos/").status_code, 403)

    def test_crud_liberado_para_administrador(self):
        logar(self.client, self.admin)
        self.assertEqual(self.client.get("/api/usuario/alunos/").status_code, 200)

    def test_crud_liberado_para_staff_do_django_admin(self):
        User.objects.create_user("ti", password="x", is_staff=True)
        self.client.login(username="ti", password="x")
        self.assertEqual(self.client.get("/api/veiculo/veiculos/").status_code, 200)

    def test_escrita_com_sessao_exige_csrf(self):
        logar(self.client, self.admin)
        resp = self.client.delete("/api/usuario/operadores/%d/" % self.porteiro.id)
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Operador.objects.filter(pk=self.porteiro.id).exists())

    def test_acesso_sem_login_e_bloqueado(self):
        self.assertEqual(self.client.post(self.saida, {"tag_rfid": "X"}).status_code, 403)

    def test_acesso_com_sessao_de_operador_e_csrf(self):
        logar(self.client, self.porteiro)
        # 400 = passou da permissão e caiu na regra de negócio (não há entrada em aberto).
        resp = self.client.post(self.saida, {"tag_rfid": "X"}, **com_csrf(self.client))
        self.assertEqual(resp.status_code, 400)

    def test_acesso_com_chave_de_dispositivo(self):
        resp = self.client.post(self.saida, {"tag_rfid": "X"}, HTTP_X_API_KEY="chave-de-teste")
        self.assertEqual(resp.status_code, 400)

    def test_acesso_com_chave_errada(self):
        resp = self.client.post(self.saida, {"tag_rfid": "X"}, HTTP_X_API_KEY="chave-errada")
        self.assertEqual(resp.status_code, 403)

    @override_settings(CAMPUSPARK_API_KEY="")
    def test_sem_chave_configurada_nenhum_dispositivo_entra(self):
        resp = self.client.post(self.saida, {"tag_rfid": "X"}, HTTP_X_API_KEY="")
        self.assertEqual(resp.status_code, 403)

    def test_reconhecimento_facial_exige_login_ou_chave(self):
        self.assertEqual(self.client.post(reverse("biometria-reconhecer")).status_code, 403)

    def test_cadastro_facial_restrito_a_administrador(self):
        logar(self.client, self.porteiro)
        resp = self.client.post(reverse("biometria-cadastro"), **com_csrf(self.client))
        self.assertEqual(resp.status_code, 403)


class OperadorInativoTest(TestCase):
    """Operador desativado perde o acesso mesmo com a sessão já aberta."""

    def setUp(self):
        self.operador = criar_operador("Administrador", "44444444444")
        logar(self.client, self.operador)
        self.operador.ativo = False
        self.operador.save()

    def test_telas_redirecionam_para_login_e_limpam_sessao(self):
        resp = self.client.get(reverse("dashboard"))
        self.assertRedirects(resp, reverse("operador-login"))
        self.assertNotIn("operador_id", self.client.session)

    def test_telas_de_administrador_tambem_bloqueiam(self):
        resp = self.client.get(reverse("lista-veiculos"))
        self.assertRedirects(resp, reverse("operador-login"))
        resp = self.client.post(reverse("dashboard-vagas"), {"vagas_carro": 1, "vagas_moto": 1})
        self.assertRedirects(resp, reverse("operador-login"))

    def test_api_bloqueia(self):
        self.assertEqual(self.client.get("/api/usuario/alunos/").status_code, 403)

    def test_tela_de_login_volta_a_aparecer(self):
        resp = self.client.get(reverse("operador-login"))
        self.assertEqual(resp.status_code, 200)
