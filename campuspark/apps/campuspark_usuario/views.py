from rest_framework import viewsets
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.decorators import method_decorator
from django.views import View

from apps.campuspark_acesso.models import ConfiguracaoEstacionamento, RegistroAcesso, StatusAcesso
from apps.campuspark_veiculo.models import TipoVeiculo, Veiculo
from core.permissions import administrador_required, get_operador_logado, operador_login_required
from core.utils import somente_numeros
from .models import Aluno, Operador
from .serializers import AlunoSerializer, OperadorSerializer
from .services import OperadorService

class AlunoViewSet(viewsets.ModelViewSet):
    queryset = Aluno.objects.all()
    serializer_class = AlunoSerializer

class OperadorViewSet(viewsets.ModelViewSet):
    queryset = Operador.objects.all()
    serializer_class = OperadorSerializer


class OperadorLoginView(View):
    """Login de administrador/operador (porteiro ou adm supremo/TI) — RNF14."""

    template_name = "operador/login.html"

    def get(self, request):
        if get_operador_logado(request) is not None:
            return redirect("dashboard")
        request.session.pop("operador_id", None)
        return render(request, self.template_name)

    def post(self, request):
        cpf = somente_numeros(request.POST.get("cpf", ""))
        senha = request.POST.get("senha", "")
        operador = OperadorService.autenticar(cpf, senha)
        if operador is None:
            return render(request, self.template_name, {
                "erro": "CPF ou senha inválidos.",
                "cpf": request.POST.get("cpf", ""),
            })
        request.session["operador_id"] = operador.id
        return redirect("dashboard")


class OperadorLogoutView(View):
    def get(self, request):
        request.session.pop("operador_id", None)
        return redirect("operador-login")


def _vagas_livres_total() -> int:
    config = ConfiguracaoEstacionamento.obter()
    dentro = RegistroAcesso.objects.filter(status=StatusAcesso.DENTRO)
    carros_dentro = dentro.filter(veiculo__tipo=TipoVeiculo.CARRO).count()
    motos_dentro = dentro.filter(veiculo__tipo=TipoVeiculo.MOTO).count()
    return max(config.vagas_carro - carros_dentro, 0) + max(config.vagas_moto - motos_dentro, 0)


@method_decorator(operador_login_required, name="dispatch")
class ListaAlunosView(View):
    """Consulta de usuários cadastrados e veículos vinculados — RF12."""

    template_name = "operador/lista_alunos.html"

    def get(self, request):
        busca = request.GET.get("busca", "").strip()
        status_filtro = request.GET.get("status", "")

        alunos = Aluno.objects.all().prefetch_related("veiculos").order_by("nome_completo")
        if busca:
            alunos = alunos.filter(
                Q(nome_completo__icontains=busca)
                | Q(matricula__icontains=busca)
                | Q(veiculos__placa__icontains=busca)
            ).distinct()
        if status_filtro == "ativo":
            alunos = alunos.filter(ativo=True)
        elif status_filtro == "inativo":
            alunos = alunos.filter(ativo=False)

        paginator = Paginator(alunos, 10)
        pagina = paginator.get_page(request.GET.get("pagina"))

        linhas = []
        for aluno in pagina.object_list:
            veiculos_do_aluno = list(aluno.veiculos.all())
            partes_nome = aluno.nome_completo.split()
            if len(partes_nome) > 1:
                iniciais = (partes_nome[0][0] + partes_nome[-1][0]).upper()
            else:
                iniciais = aluno.nome_completo[:2].upper()
            linhas.append({
                "aluno": aluno,
                "iniciais": iniciais,
                "veiculo": veiculos_do_aluno[0] if veiculos_do_aluno else None,
            })

        context = {
            "operador": request.operador,
            "secao": "alunos",
            "pagina": pagina,
            "linhas": linhas,
            "busca": busca,
            "status_filtro": status_filtro,
            "total_alunos": Aluno.objects.count(),
            "veiculos_ativos": Veiculo.objects.filter(autorizado=True).count(),
            "vagas_livres": _vagas_livres_total(),
        }
        return render(request, self.template_name, context)


@method_decorator(administrador_required, name="dispatch")
class EditarAlunoView(View):
    """Atualização cadastral de usuário — RF13, restrita a Administrador (RF15)."""

    template_name = "operador/editar_aluno.html"

    def get(self, request, aluno_id):
        aluno = get_object_or_404(Aluno, pk=aluno_id)
        return render(request, self.template_name, {"operador": request.operador, "secao": "alunos", "aluno": aluno})

    def post(self, request, aluno_id):
        aluno = get_object_or_404(Aluno, pk=aluno_id)
        aluno.nome_completo = request.POST.get("nome_completo", "").strip()
        aluno.matricula = request.POST.get("matricula", "").strip()
        aluno.email_institucional = request.POST.get("email_institucional", "").strip()
        aluno.ativo = request.POST.get("ativo") == "on"

        try:
            aluno.full_clean(exclude=["cpf", "senha_hash"])
            aluno.save()
        except ValidationError as exc:
            for erros in exc.message_dict.values():
                for erro in erros:
                    messages.error(request, erro)
            return render(request, self.template_name, {"operador": request.operador, "secao": "alunos", "aluno": aluno})

        messages.success(request, "Dados do aluno atualizados com sucesso.")
        return redirect("lista-alunos")