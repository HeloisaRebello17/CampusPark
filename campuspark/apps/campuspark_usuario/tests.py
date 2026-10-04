from django.test import TestCase
from django.urls import reverse

from apps.campuspark_veiculo.models import Veiculo
from .models import Aluno
from .services import UsuarioService

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


def criar_aluno(matricula="1234567", cpf="11111111111", email="aluno@catolicasc.org", senha="senha123"):
    return UsuarioService.cadastrar_aluno({
        "matricula": matricula,
        "cpf": cpf,
        "nome_completo": "Aluno Teste",
        "email_institucional": email,
        "senha": senha,
    })


class CadastroAlunoViewTest(TestCase):
    """Fluxo de cadastro (usuario/pages.py::cadastro_view)."""

    def setUp(self):
        self.url = reverse("cadastro")

    def dados_validos(self, **overrides):
        dados = {
            "nome": "Maria da Silva",
            "matricula": "2201934",
            "cpf": "12345678901",
            "email": "maria@catolicasc.org",
            "senha": "senha123",
        }
        dados.update(overrides)
        return dados

    def test_cadastro_valido_loga_e_redireciona_para_cadastro_de_veiculo(self):
        resp = self.client.post(self.url, self.dados_validos())
        self.assertRedirects(resp, reverse("veiculo-cadastro"))
        self.assertTrue(Aluno.objects.filter(matricula="2201934").exists())
        self.assertEqual(self.client.session["aluno_id"], Aluno.objects.get(matricula="2201934").id)

    def test_ra_com_menos_de_7_digitos_mostra_erro_especifico(self):
        resp = self.client.post(self.url, self.dados_validos(matricula="123"))
        self.assertContains(resp, "O RA deve conter exatamente 7 números.", status_code=400)
        self.assertFalse(Aluno.objects.exists())

    def test_ra_nao_numerico_mostra_erro_especifico(self):
        resp = self.client.post(self.url, self.dados_validos(matricula="abcdefg"))
        self.assertContains(resp, "O RA deve conter exatamente 7 números.", status_code=400)

    def test_ra_duplicado_mostra_erro_especifico(self):
        criar_aluno(matricula="2201934", cpf="00000000000", email="outro@catolicasc.org")
        resp = self.client.post(self.url, self.dados_validos(matricula="2201934", cpf="99999999999"))
        self.assertContains(resp, "Esse RA já possui um cadastro vinculado.", status_code=400)

    def test_cpf_com_tamanho_errado_mostra_erro_especifico(self):
        resp = self.client.post(self.url, self.dados_validos(cpf="123"))
        self.assertContains(resp, "O CPF deve conter exatamente 11 números.", status_code=400)

    def test_cpf_duplicado_mostra_erro_especifico(self):
        criar_aluno(matricula="1111111", cpf="12345678901", email="outro@catolicasc.org")
        resp = self.client.post(self.url, self.dados_validos(matricula="2222222", cpf="12345678901"))
        self.assertContains(resp, "Esse CPF já possui um cadastro vinculado.", status_code=400)

    def test_email_duplicado_mostra_erro_especifico(self):
        criar_aluno(matricula="1111111", cpf="00000000000", email="repetido@catolicasc.org")
        resp = self.client.post(self.url, self.dados_validos(matricula="2222222", cpf="99999999999", email="repetido@catolicasc.org"))
        self.assertContains(resp, "Esse e-mail já está vinculado a outro cadastro.", status_code=400)

    def test_email_duplicado_ignora_maiusculas_minusculas(self):
        criar_aluno(matricula="1111111", cpf="00000000000", email="Repetido@Catolicasc.org")
        resp = self.client.post(self.url, self.dados_validos(matricula="2222222", cpf="99999999999", email="repetido@catolicasc.org"))
        self.assertContains(resp, "Esse e-mail já está vinculado a outro cadastro.", status_code=400)

    def test_senha_curta_mostra_erro(self):
        resp = self.client.post(self.url, self.dados_validos(senha="123"))
        self.assertContains(resp, "A senha deve ter pelo menos 6 caracteres.", status_code=400)

    def test_cpf_com_pontuacao_e_aceito_normalizado(self):
        resp = self.client.post(self.url, self.dados_validos(cpf="123.456.789-01"))
        self.assertRedirects(resp, reverse("veiculo-cadastro"))
        self.assertTrue(Aluno.objects.filter(cpf="12345678901").exists())

    def test_cpf_com_letras_e_simbolos_remove_antes_de_validar(self):
        # Letras e simbolos sao removidos antes da validacao, entao um CPF
        # como "abc.123-45" vira "12345" (5 digitos) e falha por tamanho,
        # nao por conter caracteres invalidos.
        resp = self.client.post(self.url, self.dados_validos(cpf="abc.123-45"))
        self.assertContains(resp, "O CPF deve conter exatamente 11 números.", status_code=400)


class LoginAlunoViewTest(TestCase):
    """Fluxo de login (usuario/pages.py::login_view)."""

    def setUp(self):
        self.aluno = criar_aluno()
        self.url = reverse("login")

    def test_login_valido_redireciona_para_dashboard(self):
        resp = self.client.post(self.url, {"identificador": "1234567", "senha": "senha123"})
        self.assertRedirects(resp, reverse("aluno-dashboard"))
        self.assertEqual(self.client.session["aluno_id"], self.aluno.id)

    def test_senha_errada_mostra_credenciais_invalidas(self):
        resp = self.client.post(self.url, {"identificador": "1234567", "senha": "errada"})
        self.assertContains(resp, "Credenciais inválidas", status_code=401)

    def test_aluno_inativo_nao_autentica(self):
        self.aluno.ativo = False
        self.aluno.save()
        resp = self.client.post(self.url, {"identificador": "1234567", "senha": "senha123"})
        self.assertEqual(resp.status_code, 401)


class DashboardViewTest(TestCase):
    """Painel do aluno (usuario/pages.py::dashboard_view)."""

    def setUp(self):
        self.aluno = criar_aluno()
        self.url = reverse("aluno-dashboard")

    def test_exige_login(self):
        resp = self.client.get(self.url)
        self.assertRedirects(resp, reverse("login"))

    def test_sessao_com_aluno_inexistente_desloga_e_redireciona(self):
        session = self.client.session
        session["aluno_id"] = 99999
        session.save()
        resp = self.client.get(self.url)
        self.assertRedirects(resp, reverse("login"))

    def test_dashboard_logado_mostra_primeiro_nome(self):
        self.client.post(reverse("login"), {"identificador": "1234567", "senha": "senha123"})
        resp = self.client.get(self.url)
        self.assertContains(resp, "Bem-vindo, Aluno.")


class CadastroVeiculoViewTest(TestCase):
    """Cadastro de veiculo pelo aluno (usuario/pages.py::cadastro_veiculo_view)."""

    def setUp(self):
        self.aluno = criar_aluno()
        self.client.post(reverse("login"), {"identificador": "1234567", "senha": "senha123"})
        self.url = reverse("veiculo-cadastro")

    def test_exige_login(self):
        deslogado = self.client_class()
        resp = deslogado.get(self.url)
        self.assertRedirects(resp, reverse("login"))

    def test_cadastro_valido_cria_veiculo_vinculado_ao_aluno(self):
        resp = self.client.post(self.url, {
            "tipo_veiculo": "automovel",
            "placa": "ABC1234",
            "modelo_ano": "Honda Civic 2022",
        })
        self.assertRedirects(resp, reverse("aluno-dashboard"))
        veiculo = Veiculo.objects.get(placa="ABC1234")
        self.assertEqual(veiculo.aluno_id, self.aluno.id)
        self.assertEqual(veiculo.tipo, "carro")
        self.assertIsNone(veiculo.tag_rfid)
        self.assertIsNone(veiculo.renavam)

    def test_tipo_motocicleta_mapeia_para_moto(self):
        self.client.post(self.url, {"tipo_veiculo": "motocicleta", "placa": "XYZ9876", "modelo_ano": ""})
        self.assertTrue(Veiculo.objects.filter(placa="XYZ9876", tipo="moto").exists())

    def test_placa_e_normalizada_para_maiuscula_sem_traco_ou_espaco(self):
        self.client.post(self.url, {"tipo_veiculo": "automovel", "placa": "abc-12 34", "modelo_ano": ""})
        self.assertTrue(Veiculo.objects.filter(placa="ABC1234").exists())

    def test_placa_vazia_mostra_erro(self):
        resp = self.client.post(self.url, {"tipo_veiculo": "automovel", "placa": "", "modelo_ano": ""})
        self.assertContains(resp, "Informe a placa do veículo.", status_code=400)
        self.assertEqual(Veiculo.objects.count(), 0)

    def test_placa_remove_caracteres_especiais(self):
        self.client.post(self.url, {"tipo_veiculo": "automovel", "placa": "AB#C-12!34", "modelo_ano": ""})
        self.assertTrue(Veiculo.objects.filter(placa="ABC1234").exists())

    def test_placa_somente_espacos_mostra_erro(self):
        resp = self.client.post(self.url, {"tipo_veiculo": "automovel", "placa": "   ", "modelo_ano": ""})
        self.assertContains(resp, "Informe a placa do veículo.", status_code=400)
        self.assertEqual(Veiculo.objects.count(), 0)

    def test_placa_somente_simbolos_mostra_erro(self):
        resp = self.client.post(self.url, {"tipo_veiculo": "automovel", "placa": "!!!---", "modelo_ano": ""})
        self.assertContains(resp, "Informe a placa do veículo.", status_code=400)
        self.assertEqual(Veiculo.objects.count(), 0)

    def test_placa_duplicada_mostra_erro_e_nao_duplica(self):
        Veiculo.objects.create(aluno=self.aluno, placa="ABC1234", tipo="carro")
        resp = self.client.post(self.url, {"tipo_veiculo": "automovel", "placa": "ABC1234", "modelo_ano": ""})
        self.assertContains(resp, "Já existe um veículo cadastrado com essa placa.", status_code=400)
        self.assertEqual(Veiculo.objects.filter(placa="ABC1234").count(), 1)

    def test_dois_veiculos_sem_tag_rfid_nao_colidem(self):
        # Regressao: tag_rfid/renavam nao podem ficar como string vazia (o
        # default do Django para CharField), senao o segundo veiculo sem tag
        # esbarra num erro de unicidade que nao tem nada a ver com a placa.
        primeiro = self.client.post(self.url, {"tipo_veiculo": "automovel", "placa": "AAA1111", "modelo_ano": ""})
        segundo = self.client.post(self.url, {"tipo_veiculo": "automovel", "placa": "BBB2222", "modelo_ano": ""})
        self.assertRedirects(primeiro, reverse("aluno-dashboard"))
        self.assertRedirects(segundo, reverse("aluno-dashboard"))
        self.assertEqual(Veiculo.objects.filter(aluno=self.aluno).count(), 2)


class MeusVeiculosViewTest(TestCase):
    """Lista de veiculos do aluno (usuario/pages.py::meus_veiculos_view)."""

    def setUp(self):
        self.aluno = criar_aluno()
        self.outro_aluno = criar_aluno(matricula="7654321", cpf="99999999999", email="outro@catolicasc.org")
        self.client.post(reverse("login"), {"identificador": "1234567", "senha": "senha123"})
        self.url = reverse("meus-veiculos")

    def test_exige_login(self):
        deslogado = self.client_class()
        resp = deslogado.get(self.url)
        self.assertRedirects(resp, reverse("login"))

    def test_lista_vazia_mostra_mensagem(self):
        resp = self.client.get(self.url)
        self.assertContains(resp, "Você ainda não cadastrou nenhum veículo.")

    def test_mostra_apenas_veiculos_do_proprio_aluno(self):
        Veiculo.objects.create(aluno=self.aluno, placa="AAA1111", tipo="carro")
        Veiculo.objects.create(aluno=self.outro_aluno, placa="BBB2222", tipo="moto")
        resp = self.client.get(self.url)
        self.assertContains(resp, "AAA-1111")
        self.assertNotContains(resp, "BBB-2222")
