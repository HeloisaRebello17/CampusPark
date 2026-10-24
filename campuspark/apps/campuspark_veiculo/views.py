import re

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from rest_framework import viewsets

from apps.campuspark_acesso.models import RegistroAcesso, StatusAcesso
from core.permissions import administrador_required, operador_login_required
from .models import TipoVeiculo, Veiculo
from .serializers import VeiculoSerializer
from .services import OperacaoVeiculoNegada, VeiculoService
from .validators import PLACA_REGEX


class VeiculoViewSet(viewsets.ModelViewSet):
    queryset = Veiculo.objects.all()
    serializer_class = VeiculoSerializer


def _voltar_para_lista(request):
    """Volta para a lista mantendo busca/filtro/página, se o 'next' for uma URL interna."""
    destino = request.POST.get("next", "")
    if destino and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        return redirect(destino)
    return redirect("lista-veiculos")


@method_decorator(operador_login_required, name="dispatch")
class ListaVeiculosView(View):
    """Consulta de veículos cadastrados, com situação de autorização — RF12, RF13."""

    template_name = "operador/lista_veiculos.html"

    def get(self, request):
        busca = request.GET.get("busca", "").strip()
        autorizacao = request.GET.get("autorizacao", "")

        veiculos = (
            Veiculo.objects.select_related("aluno")
            .annotate(no_estacionamento=Exists(
                RegistroAcesso.objects.filter(veiculo=OuterRef("pk"), status=StatusAcesso.DENTRO)
            ))
            .order_by("placa")
        )
        if busca:
            veiculos = veiculos.filter(
                Q(placa__icontains=busca)
                | Q(aluno__nome_completo__icontains=busca)
                | Q(aluno__matricula__icontains=busca)
            )
        if autorizacao == "autorizado":
            veiculos = veiculos.filter(autorizado=True)
        elif autorizacao == "bloqueado":
            veiculos = veiculos.filter(autorizado=False)

        pagina = Paginator(veiculos, 10).get_page(request.GET.get("pagina"))

        context = {
            "operador": request.operador,
            "secao": "veiculos",
            "pagina": pagina,
            "busca": busca,
            "autorizacao": autorizacao,
            "total_veiculos": Veiculo.objects.count(),
            "total_autorizados": Veiculo.objects.filter(autorizado=True).count(),
            "total_bloqueados": Veiculo.objects.filter(autorizado=False).count(),
        }
        return render(request, self.template_name, context)


@method_decorator(operador_login_required, name="dispatch")
class AutorizacaoVeiculoView(View):
    """Autoriza ou bloqueia um veículo — exclusivo de operadores (RF13, RF15)."""

    def post(self, request, veiculo_id):
        veiculo = get_object_or_404(Veiculo, pk=veiculo_id)
        autorizar = request.POST.get("autorizado") == "1"
        VeiculoService.alterar_autorizacao(veiculo, autorizar)
        if autorizar:
            messages.success(request, f"Veículo {veiculo.placa} autorizado.")
        else:
            messages.success(request, f"Veículo {veiculo.placa} bloqueado. Novas entradas serão negadas.")
        return _voltar_para_lista(request)


@method_decorator(administrador_required, name="dispatch")
class EditarVeiculoView(View):
    """Atualização cadastral de veículo, incluindo autorização — RF13, restrita a Administrador (RF15)."""

    template_name = "operador/editar_veiculo.html"

    def _render(self, request, veiculo, status=200):
        return render(request, self.template_name, {
            "operador": request.operador,
            "secao": "veiculos",
            "veiculo": veiculo,
            "tipos": TipoVeiculo.choices,
        }, status=status)

    def _bloqueado_se_dentro(self, request, veiculo):
        try:
            VeiculoService.garantir_fora_do_estacionamento(veiculo)
        except OperacaoVeiculoNegada as e:
            messages.error(request, str(e))
            return redirect("lista-veiculos")
        return None

    def get(self, request, veiculo_id):
        veiculo = get_object_or_404(Veiculo.objects.select_related("aluno"), pk=veiculo_id)
        return self._bloqueado_se_dentro(request, veiculo) or self._render(request, veiculo)

    def post(self, request, veiculo_id):
        veiculo = get_object_or_404(Veiculo.objects.select_related("aluno"), pk=veiculo_id)
        bloqueio = self._bloqueado_se_dentro(request, veiculo)
        if bloqueio:
            return bloqueio

        veiculo.placa = re.sub(r"[^A-Za-z0-9]", "", request.POST.get("placa", "")).upper()
        veiculo.tipo = request.POST.get("tipo", "")
        veiculo.fabricante = request.POST.get("fabricante", "").strip()
        veiculo.modelo = request.POST.get("modelo", "").strip()
        veiculo.cor = request.POST.get("cor", "").strip()
        veiculo.seguro_ativo = request.POST.get("seguro_ativo") == "on"
        veiculo.autorizado = request.POST.get("autorizado") == "on"

        erros = []
        if not PLACA_REGEX.match(veiculo.placa):
            erros.append("Placa inválida. Use o formato Mercosul, ex: ABC1D23.")
        if veiculo.tipo not in TipoVeiculo.values:
            erros.append("Selecione um tipo de veículo válido.")
        if len(veiculo.fabricante) > 30 or len(veiculo.modelo) > 30 or len(veiculo.cor) > 20:
            erros.append("Fabricante e modelo aceitam até 30 caracteres; cor, até 20.")

        if not erros:
            try:
                with transaction.atomic():
                    veiculo.save()
            except IntegrityError:
                erros.append("Já existe um veículo cadastrado com essa placa.")
            else:
                messages.success(request, f"Veículo {veiculo.placa} atualizado com sucesso.")
                return redirect("lista-veiculos")

        for erro in erros:
            messages.error(request, erro)
        return self._render(request, veiculo, status=400)


@method_decorator(administrador_required, name="dispatch")
class ExcluirVeiculoView(View):
    """Exclusão de veículo — restrita a Administrador (RF15)."""

    def post(self, request, veiculo_id):
        veiculo = get_object_or_404(Veiculo, pk=veiculo_id)
        placa = veiculo.placa
        try:
            VeiculoService.excluir(veiculo)
        except OperacaoVeiculoNegada as e:
            messages.error(request, str(e))
        else:
            messages.success(request, f"Veículo {placa} removido.")
        return _voltar_para_lista(request)
