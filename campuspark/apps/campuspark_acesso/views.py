from apps.campuspark_usuario.models import Aluno
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.campuspark_veiculo.models import TipoVeiculo
from core.permissions import operador_login_required, administrador_required
from .services import AcessoService, AcessoNegado, anunciar_rosto, anunciar_acesso
from .serializers import RegistroAcessoSerializer
from .models import (
    RegistroAcesso, StatusAcesso, ConfiguracaoEstacionamento,
    AberturaCancela, SentidoAbertura,
)


@method_decorator(operador_login_required, name="dispatch")
class DashboardView(View):
    """Tela inicial: vagas, veículos dentro do estacionamento e histórico de acessos (RF10, RF12)."""

    template_name = "operador/dashboard.html"

    def get(self, request):
        config = ConfiguracaoEstacionamento.obter()
        dentro = RegistroAcesso.objects.filter(status=StatusAcesso.DENTRO).select_related("veiculo")
        carros_dentro = dentro.filter(veiculo__tipo=TipoVeiculo.CARRO).count()
        motos_dentro = dentro.filter(veiculo__tipo=TipoVeiculo.MOTO).count()
        historico = (
            RegistroAcesso.objects
            .select_related("veiculo", "veiculo__aluno", "operador")
            .order_by("-data_entrada")[:50]
        )
        context = {
            "operador": request.operador,
            "secao": "dashboard",
            "config": config,
            "carros_dentro": carros_dentro,
            "motos_dentro": motos_dentro,
            "vagas_carro_livres": max(config.vagas_carro - carros_dentro, 0),
            "vagas_moto_livres": max(config.vagas_moto - motos_dentro, 0),
            "historico": historico,
        }
        return render(request, self.template_name, context)


@method_decorator(administrador_required, name="dispatch")
class AtualizarVagasView(View):
    """Atualiza a capacidade máxima de vagas (carro/moto) — restrito a Administrador (RF15)."""

    def post(self, request):
        config = ConfiguracaoEstacionamento.obter()
        try:
            vagas_carro = int(request.POST.get("vagas_carro", ""))
            vagas_moto = int(request.POST.get("vagas_moto", ""))
            if vagas_carro < 0 or vagas_moto < 0:
                raise ValueError
        except ValueError:
            messages.error(request, "Informe valores numéricos válidos para as vagas.")
            return redirect("dashboard")

        config.vagas_carro = vagas_carro
        config.vagas_moto = vagas_moto
        config.save(update_fields=["vagas_carro", "vagas_moto"])
        messages.success(request, "Capacidade do estacionamento atualizada com sucesso.")
        return redirect("dashboard")


@method_decorator(operador_login_required, name="dispatch")
class CancelaView(View):
    """Controle da cancela: simulação da liberação automática (TAG + rosto), liberação manual
    pelo operador e histórico das últimas aberturas."""

    template_name = "operador/cancela.html"

    def _contexto(self, request, **extra):
        aberturas = (
            AberturaCancela.objects
            .select_related("veiculo", "operador")
            .order_by("-data_hora")[:30]
        )
        context = {
            "operador": request.operador,
            "secao": "cancela",
            "aberturas": aberturas,
        }
        context.update(extra)
        return context

    def get(self, request):
        return render(request, self.template_name, self._contexto(request))

    def post(self, request):
        acao = request.POST.get("acao")
        if acao == "simular":
            return self._simular(request)
        if acao == "manual":
            return self._manual(request)
        return render(request, self.template_name, self._contexto(request))

    def _simular(self, request):
        tag = request.POST.get("tag_rfid", "").strip()
        matricula = request.POST.get("matricula", "").strip()
        sentido = request.POST.get("sentido", SentidoAbertura.ENTRADA)
        extra = {"tag_digitada": tag, "matricula_digitada": matricula}

        aluno = None
        if sentido == SentidoAbertura.ENTRADA and matricula:
            aluno = Aluno.objects.filter(matricula=matricula).first()
            if aluno is None:
                extra["erro_auto"] = "Aluno com essa matrícula não foi encontrado."
                return render(request, self.template_name, self._contexto(request, **extra))
            anunciar_rosto(aluno)

        try:
            if sentido == SentidoAbertura.SAIDA:
                registro = AcessoService.registrar_saida(tag)
            else:
                sentido = SentidoAbertura.ENTRADA
                registro = AcessoService.validar_entrada(tag, aluno_reconhecido=aluno)
        except AcessoNegado as e:
            print(f"[ACESSO NEGADO] {e}")
            extra["erro_auto"] = str(e)
            return render(request, self.template_name, self._contexto(request, **extra))

        anunciar_acesso(registro, sentido)
        extra["resultado"] = {
            "sentido": "Entrada" if sentido == SentidoAbertura.ENTRADA else "Saída",
            "placa": registro.veiculo.placa,
            "aluno": registro.veiculo.aluno.nome_completo,
            "matricula": registro.veiculo.aluno.matricula,
            "entrada": registro.data_entrada,
            "saida": registro.data_saida,
            "permanencia": str(registro.permanencia).split(".")[0],
            "rosto_verificado": aluno is not None,
        }
        return render(request, self.template_name, self._contexto(request, **extra))

    def _manual(self, request):
        try:
            AcessoService.liberar_manual(
                request.operador,
                request.POST.get("sentido", ""),
                request.POST.get("motivo", ""),
                request.POST.get("placa", ""),
            )
        except AcessoNegado as e:
            extra = {"erro_manual": str(e)}
        else:
            extra = {"sucesso_manual": "Cancela aberta manualmente. A abertura foi registrada no histórico."}
        return render(request, self.template_name, self._contexto(request, **extra))


class EntradaView(APIView):
    def post(self, request):
        tag = request.data.get("tag_rfid")
        aluno_id = request.data.get("aluno_id")  # vem do reconhecimento facial (Thomas)

        aluno_reconhecido = None
        if aluno_id is not None:
            aluno_reconhecido = Aluno.objects.filter(pk=aluno_id).first()
            if aluno_reconhecido is None:
                return Response(
                    {"erro": "Aluno reconhecido pela face não encontrado no sistema."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            registro = AcessoService.validar_entrada(tag, aluno_reconhecido=aluno_reconhecido)
        except AcessoNegado as e:
            return Response({"erro": str(e)}, status=status.HTTP_403_FORBIDDEN)
        return Response(RegistroAcessoSerializer(registro).data, status=201)


class SaidaView(APIView):
    def post(self, request):
        tag = request.data.get("tag_rfid")
        try:
            registro = AcessoService.registrar_saida(tag)
        except AcessoNegado as e:
            return Response({"erro": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RegistroAcessoSerializer(registro).data, status=200)
