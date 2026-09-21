from functools import wraps

from django.db import IntegrityError
from django.shortcuts import render, redirect

from apps.campuspark_acesso.models import RegistroAcesso, StatusAcesso
from apps.campuspark_veiculo.models import TipoVeiculo, Veiculo
from .models import Aluno, Operador
from .services import UsuarioService

SESSION_ALUNO_ID = "aluno_id"
SESSION_OPERADOR_ID = "operador_id"


def aluno_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        aluno_id = request.session.get(SESSION_ALUNO_ID)
        if not aluno_id:
            return redirect("login")
        try:
            request.aluno = Aluno.objects.get(id=aluno_id, ativo=True)
        except Aluno.DoesNotExist:
            request.session.flush()
            return redirect("login")
        return view_func(request, *args, **kwargs)

    return wrapper


def operador_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        operador_id = request.session.get(SESSION_OPERADOR_ID)
        if not operador_id:
            return redirect("login")
        try:
            request.operador = Operador.objects.get(id=operador_id, ativo=True)
        except Operador.DoesNotExist:
            request.session.flush()
            return redirect("login")
        return view_func(request, *args, **kwargs)

    return wrapper


def login_view(request):
    if request.method == "POST":
        tipo = request.POST.get("tipo", "aluno")
        identificador = request.POST.get("identificador", "").strip()
        senha = request.POST.get("senha", "")

        if tipo != "operador":
            aluno = UsuarioService.autenticar(identificador, senha)
            if aluno:
                request.session.flush()
                request.session[SESSION_ALUNO_ID] = aluno.id
                return redirect("aluno-dashboard")

        return render(
            request,
            "usuario/login.html",
            {"erro": "Credenciais inválidas. Verifique os dados e tente novamente.", "tipo_selecionado": tipo},
            status=401,
        )

    return render(request, "usuario/login.html")


def cadastro_view(request):
    if request.method == "POST":
        valores = {
            "nome": request.POST.get("nome", "").strip(),
            "matricula": request.POST.get("matricula", "").strip(),
            "cpf": request.POST.get("cpf", "").strip(),
            "email": request.POST.get("email", "").strip(),
        }
        senha = request.POST.get("senha", "")

        erros = []
        if not valores["nome"]:
            erros.append("Informe seu nome completo.")

        if not valores["matricula"]:
            erros.append("Informe sua matrícula.")
        elif not valores["matricula"].isdigit() or len(valores["matricula"]) != 7:
            erros.append("O RA deve conter exatamente 7 números.")
        elif Aluno.objects.filter(matricula=valores["matricula"]).exists():
            erros.append("Esse RA já possui um cadastro vinculado.")

        if not valores["cpf"] or not valores["cpf"].isdigit():
            erros.append("Informe um CPF válido (somente números).")
        elif len(valores["cpf"]) != 11:
            erros.append("O CPF deve conter exatamente 11 números.")
        elif Aluno.objects.filter(cpf=valores["cpf"]).exists():
            erros.append("Esse CPF já possui um cadastro vinculado.")

        if not valores["email"]:
            erros.append("Informe seu e-mail institucional.")
        elif Aluno.objects.filter(email_institucional__iexact=valores["email"]).exists():
            erros.append("Esse e-mail já está vinculado a outro cadastro.")

        if len(senha) < 6:
            erros.append("A senha deve ter pelo menos 6 caracteres.")

        if not erros:
            try:
                aluno = UsuarioService.cadastrar_aluno({
                    "matricula": valores["matricula"],
                    "cpf": valores["cpf"],
                    "nome_completo": valores["nome"],
                    "email_institucional": valores["email"],
                    "senha": senha,
                })
            except IntegrityError:
                erros.append("Não foi possível concluir o cadastro. Verifique os dados informados.")
            else:
                request.session.flush()
                request.session[SESSION_ALUNO_ID] = aluno.id
                return redirect("veiculo-cadastro")

        return render(request, "usuario/cadastro.html", {"erros": erros, "valores": valores}, status=400)

    return render(request, "usuario/cadastro.html")


def logout_view(request):
    request.session.flush()
    return redirect("login")


@aluno_required
def dashboard_view(request):
    veiculos = list(Veiculo.objects.filter(aluno=request.aluno).order_by("placa"))

    dentro_ids = set(
        RegistroAcesso.objects.filter(
            veiculo__in=veiculos, status=StatusAcesso.DENTRO
        ).values_list("veiculo_id", flat=True)
    )
    for veiculo in veiculos:
        veiculo.esta_no_campus = veiculo.id in dentro_ids

    ultimo_registro = (
        RegistroAcesso.objects.filter(veiculo__in=veiculos)
        .select_related("veiculo")
        .order_by("-data_entrada")
        .first()
    )

    primeiro_nome = request.aluno.nome_completo.strip().split(" ")[0] if request.aluno.nome_completo else ""

    return render(request, "usuario/dashboard.html", {
        "aluno": request.aluno,
        "primeiro_nome": primeiro_nome,
        "veiculos": veiculos,
        "veiculos_no_campus": len(dentro_ids),
        "ultimo_registro": ultimo_registro,
    })


@aluno_required
def cadastro_veiculo_view(request):
    if request.method == "POST":
        valores = {
            "tipo_veiculo": request.POST.get("tipo_veiculo", "automovel"),
            "placa": request.POST.get("placa", "").strip().upper().replace("-", "").replace(" ", ""),
            "modelo_ano": request.POST.get("modelo_ano", "").strip(),
        }
        seguro_ativo = request.POST.get("seguro_ativo") == "on"

        erros = []
        if not valores["placa"]:
            erros.append("Informe a placa do veículo.")
        elif len(valores["placa"]) > 7:
            erros.append("Placa inválida. Use até 7 caracteres (ex: ABC1D23).")

        tipo_map = {
            "automovel": TipoVeiculo.CARRO,
            "motocicleta": TipoVeiculo.MOTO,
        }

        if not erros:
            try:
                Veiculo.objects.create(
                    placa=valores["placa"],
                    aluno=request.aluno,
                    tipo=tipo_map.get(valores["tipo_veiculo"], TipoVeiculo.CARRO),
                    modelo=valores["modelo_ano"],
                    seguro_ativo=seguro_ativo,
                    renavam=None,
                    tag_rfid=None,
                )
            except IntegrityError:
                erros.append("Já existe um veículo cadastrado com essa placa.")
            else:
                return redirect("aluno-dashboard")

        return render(request, "veiculo/cadastro_veiculo.html", {
            "aluno": request.aluno,
            "erros": erros,
            "valores": valores,
            "seguro_ativo": seguro_ativo,
        }, status=400)

    return render(request, "veiculo/cadastro_veiculo.html", {"aluno": request.aluno})


@aluno_required
def meus_veiculos_view(request):
    veiculos = Veiculo.objects.filter(aluno=request.aluno).order_by("-id")
    return render(request, "veiculo/meus_veiculos.html", {"aluno": request.aluno, "veiculos": veiculos})
