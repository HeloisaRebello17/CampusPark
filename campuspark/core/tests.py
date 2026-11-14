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


from unittest.mock import patch
from django.core.cache import cache
from core.exportacao import ExportacaoBloqueada, ip_do_request, registrar_exportacao

@override_settings(
    EXPORTACAO_INTERVALO_MINIMO=30, EXPORTACAO_JANELA=600,
    EXPORTACAO_MAX_POR_JANELA=3, EXPORTACAO_BLOQUEIO=900, EXPORTACAO_IP_MAX_POR_JANELA=5,
)
class TravaExportacaoTest(TestCase):
    """Trava por tempo e bloqueio por IP/usuário na exportação de CSV."""

    def setUp(self):
        cache.clear()
        self.agora = 1_000_000.0
        relogio = patch("core.exportacao.time.time", side_effect=lambda: self.agora)
        relogio.start()
        self.addCleanup(relogio.stop)

    def exportar(self, perfil="operador", usuario_id=1, ip="10.0.0.1"):
        registrar_exportacao(perfil, usuario_id, ip)

    def test_primeira_exportacao_e_liberada(self):
        self.exportar()

    def test_intervalo_minimo_entre_exportacoes(self):
        self.exportar()
        self.agora += 10
        with self.assertRaises(ExportacaoBloqueada) as erro:
            self.exportar()
        self.assertEqual(erro.exception.segundos, 20)
        self.assertIn("Aguarde 20 segundos", str(erro.exception))
        self.agora += 20
        self.exportar()

    def test_estourar_limite_bloqueia_o_usuario(self):
        for _ in range(3):
            self.exportar()
            self.agora += 31
        with self.assertRaises(ExportacaoBloqueada) as erro:
            self.exportar()
        self.assertEqual(erro.exception.segundos, 900)

        # Continua bloqueado durante o período, mesmo depois que a janela "esvazia".
        self.agora += 899
        with self.assertRaises(ExportacaoBloqueada) as erro:
            self.exportar()
        self.assertIn("excesso de tentativas", str(erro.exception))

        self.agora += 1
        self.exportar()

    def test_exportacoes_antigas_saem_da_janela(self):
        for _ in range(3):
            self.exportar()
            self.agora += 31
        self.agora += 600  # as 3 anteriores já saíram da janela de 10 min
        self.exportar()

    def test_bloqueio_e_por_usuario(self):
        self.exportar(usuario_id=1)
        self.exportar(usuario_id=2)                  # outro operador não é afetado
        self.exportar(perfil="aluno", usuario_id=1)  # aluno com o mesmo id também não
        with self.assertRaises(ExportacaoBloqueada):
            self.exportar(usuario_id=1)

    def test_trocar_de_ip_nao_burla_o_bloqueio_do_usuario(self):
        self.exportar(ip="10.0.0.1")
        with self.assertRaises(ExportacaoBloqueada):
            self.exportar(ip="10.0.0.2")

    def test_varias_contas_no_mesmo_ip_bloqueiam_o_ip(self):
        for usuario_id in range(1, 6):  # 5 contas diferentes, limite do IP = 5
            self.exportar(usuario_id=usuario_id)
        with self.assertRaises(ExportacaoBloqueada) as erro:
            self.exportar(usuario_id=6)
        self.assertIn("deste endereço de rede", str(erro.exception))
        self.assertEqual(erro.exception.segundos, 900)

        # O bloqueio é do IP: a mesma conta (nova) de outro IP continua exportando.
        self.exportar(usuario_id=6, ip="10.0.0.2")
        with self.assertRaises(ExportacaoBloqueada):
            self.exportar(usuario_id=7, ip="10.0.0.1")

    def test_negada_pelo_ip_nao_conta_para_o_usuario(self):
        for usuario_id in range(1, 6):
            self.exportar(usuario_id=usuario_id)
        for _ in range(3):  # negadas pelo IP: não podem gastar o limite do usuário 9
            with self.assertRaises(ExportacaoBloqueada):
                self.exportar(usuario_id=9)
        self.exportar(usuario_id=9, ip="10.0.0.2")

    def test_ip_nao_tem_intervalo_minimo(self):
        self.exportar(usuario_id=1)
        self.exportar(usuario_id=2)  # mesmo IP, logo em seguida: liberado


class IpDoRequestTest(TestCase):
    def requisicao(self, **meta):
        from django.test import RequestFactory
        return RequestFactory().get("/", REMOTE_ADDR="10.0.0.1", **meta)

    @override_settings(EXPORTACAO_CONFIAR_PROXY=False)
    def test_ignora_x_forwarded_for_sem_proxy_confiavel(self):
        req = self.requisicao(HTTP_X_FORWARDED_FOR="1.2.3.4")
        self.assertEqual(ip_do_request(req), "10.0.0.1")

    @override_settings(EXPORTACAO_CONFIAR_PROXY=True)
    def test_com_proxy_confiavel_usa_ip_adicionado_pelo_proxy(self):
        # "1.2.3.4" foi forjado pelo cliente; "200.1.1.1" foi o que o proxy adicionou.
        req = self.requisicao(HTTP_X_FORWARDED_FOR="1.2.3.4, 200.1.1.1")
        self.assertEqual(ip_do_request(req), "200.1.1.1")


class TravaExportacaoViewTest(TestCase):
    """A trava aplicada na tela de histórico do operador."""

    def setUp(self):
        cache.clear()
        logar(self.client, criar_operador("Porteiro", "44444444444"))
        self.url = reverse("historico-exportar")

    def test_csv_nao_fica_em_cache(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp["Cache-Control"], "no-store")

    def test_exportacao_seguida_volta_ao_historico_com_aviso_e_filtros(self):
        self.client.get(self.url, {"tipo": "moto"})
        resp = self.client.get(self.url, {"tipo": "moto"}, follow=True)
        self.assertRedirects(resp, reverse("historico-acessos") + "?tipo=moto")
        self.assertContains(resp, "antes de exportar novamente")

    @override_settings(EXPORTACAO_IP_MAX_POR_JANELA=1)
    def test_outro_operador_no_mesmo_ip_bloqueado(self):
        self.client.get(self.url)
        outro = Client(REMOTE_ADDR="127.0.0.1")
        logar(outro, criar_operador("Porteiro", "55555555555"))
        # O 1º operador já usou o limite do IP: a conta nova, no mesmo IP, é barrada.
        resp = outro.get(self.url, follow=True)
        self.assertContains(resp, "deste endereço de rede")

    def test_exportacao_liberada_e_negada_saem_no_log_com_usuario_e_ip(self):
        operador_id = self.client.session["operador_id"]
        with self.assertLogs("campuspark.exportacao", level="INFO") as log:
            self.client.get(self.url, {"tipo": "moto"})
            self.client.get(self.url)
        self.assertIn(
            f"INFO:campuspark.exportacao:Exportação liberada: operador id={operador_id} ip=127.0.0.1 historico ?tipo=moto",
            log.output,
        )
        self.assertTrue(any(
            linha.startswith("WARNING:") and f"Exportação negada: operador id={operador_id} ip=127.0.0.1" in linha
            for linha in log.output
        ))

    def test_aviso_traz_contagem_regressiva(self):
        self.client.get(self.url)
        resp = self.client.get(self.url, follow=True)
        html = resp.content.decode()
        # O <span> chega como HTML (não escapado) para o ui.js fazer a contagem.
        self.assertRegex(html, r'Aguarde <span class="contagem" data-contagem="(\d+)">\1 segundos?</span> antes')
        self.assertNotIn("&lt;span", html)


class TempoRestanteTest(TestCase):
    def test_formato_igual_ao_do_ui_js(self):
        from core.exportacao import tempo_restante
        self.assertEqual(tempo_restante(1), "1 segundo")
        self.assertEqual(tempo_restante(25), "25 segundos")
        self.assertEqual(tempo_restante(60), "1 min 00 s")
        self.assertEqual(tempo_restante(845), "14 min 05 s")

    def test_html_escapa_o_texto_e_mantem_so_o_span(self):
        erro = ExportacaoBloqueada("<b>x</b> em {tempo}.", 25)
        self.assertEqual(str(erro), "<b>x</b> em 25 segundos.")
        self.assertEqual(
            erro.como_html(),
            '&lt;b&gt;x&lt;/b&gt; em <span class="contagem" data-contagem="25">25 segundos</span>.',
        )
