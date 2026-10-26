import re
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.campuspark_acesso.historico import COLUNAS_ALUNO, resposta_csv
from apps.campuspark_acesso.models import RegistroAcesso, StatusAcesso
from apps.campuspark_biometria.services import BiometriaService, RostoNaoDetectado
from apps.campuspark_veiculo.models import TipoVeiculo, Veiculo
from apps.campuspark_veiculo.services import OperacaoVeiculoNegada, VeiculoService
from apps.campuspark_veiculo.validators import PLACA_REGEX
from core.utils import somente_numeros
from .models import Aluno, Operador
from .services import UsuarioService

SESSION_ALUNO_ID = "aluno_id"
SESSION_OPERADOR_ID = "operador_id"

MESES_PT = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]

# Fotos do rosto tiradas no cadastro (reconhecimento facial na saida).
# A tela captura FOTOS_ROSTO_ALVO; o servidor exige que pelo menos FOTOS_ROSTO_MINIMO
# tenham rosto detectavel, senao o cadastro inteiro e desfeito.
FOTOS_ROSTO_ALVO = 5
FOTOS_ROSTO_MINIMO = 3
FOTOS_ROSTO_MAXIMO = 10


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


def _contexto_cadastro(**extra):
    """Contexto base da tela de cadastro (parametros da captura facial)."""
    contexto = {
        "fotos_alvo": FOTOS_ROSTO_ALVO,
        # Upload de arquivo no lugar da camera so em desenvolvimento (DEBUG):
        # em producao a foto precisa vir da camera, nao de uma imagem qualquer.
        "permitir_upload_foto": settings.DEBUG,
    }
    contexto.update(extra)
    return contexto


def cadastro_view(request):
    if request.method == "POST":
        valores = {
            "nome": request.POST.get("nome", "").strip(),
            "matricula": request.POST.get("matricula", "").strip(),
            "cpf": somente_numeros(request.POST.get("cpf", "")),
            "email": request.POST.get("email", "").strip(),
        }
        senha = request.POST.get("senha", "")
        fotos_rosto = request.FILES.getlist("fotos_rosto")

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

        if len(fotos_rosto) < FOTOS_ROSTO_MINIMO:
            erros.append("Tire as fotos do seu rosto para concluir o cadastro.")
        elif len(fotos_rosto) > FOTOS_ROSTO_MAXIMO:
            erros.append(f"Envie no máximo {FOTOS_ROSTO_MAXIMO} fotos do rosto.")

        if not erros:
            try:
                # Aluno e biometria no mesmo bloco: se o rosto nao for detectado,
                # o aluno tambem nao e criado.
                with transaction.atomic():
                    aluno = UsuarioService.cadastrar_aluno({
                        "matricula": valores["matricula"],
                        "cpf": valores["cpf"],
                        "nome_completo": valores["nome"],
                        "email_institucional": valores["email"],
                        "senha": senha,
                    })
                    BiometriaService.cadastrar(aluno, fotos_rosto, minimo_amostras=FOTOS_ROSTO_MINIMO)
            except IntegrityError:
                erros.append("Não foi possível concluir o cadastro. Verifique os dados informados.")
            except RostoNaoDetectado:
                erros.append(
                    "Não conseguimos detectar seu rosto nas fotos. Fique de frente para a câmera, "
                    "com boa iluminação e sem boné ou óculos escuros, e tire as fotos novamente."
                )
            except FileNotFoundError:
                erros.append(
                    "O reconhecimento facial está indisponível no momento. "
                    "Procure o suporte do estacionamento."
                )
            else:
                request.session.flush()
                request.session[SESSION_ALUNO_ID] = aluno.id
                return redirect("veiculo-cadastro")

        return render(
            request, "usuario/cadastro.html",
            _contexto_cadastro(erros=erros, valores=valores), status=400,
        )

    return render(request, "usuario/cadastro.html", _contexto_cadastro())


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

    agora = timezone.localtime()
    registros_mes = RegistroAcesso.objects.filter(
        veiculo__in=veiculos, data_entrada__year=agora.year, data_entrada__month=agora.month,
    ).count()
    mes_atual = f"{MESES_PT[agora.month - 1].capitalize()} de {agora.year}"

    return render(request, "usuario/dashboard.html", {
        "aluno": request.aluno,
        "primeiro_nome": primeiro_nome,
        "veiculos": veiculos,
        "veiculos_no_campus": len(dentro_ids),
        "ultimo_registro": ultimo_registro,
        "mes_atual": mes_atual,
        "mes_input": f"{agora.year}-{agora.month:02d}",
        "registros_mes": registros_mes,
    })


def _mes_do_relatorio(texto: str):
    """Lê o mês escolhido ('AAAA-MM'); vazio ou inválido vira o mês atual."""
    agora = timezone.localtime()
    try:
        ano, mes = (int(parte) for parte in texto.split("-"))
        if 1 <= mes <= 12 and 2000 <= ano <= agora.year:
            return ano, mes
    except ValueError:
        pass
    return agora.year, agora.month


@aluno_required
def relatorio_mensal_view(request):
    """Exporta em CSV os acessos (entrada/saida) do mes escolhido (padrao: mes atual) do aluno logado."""
    ano, mes = _mes_do_relatorio(request.GET.get("mes", ""))
    registros = (
        RegistroAcesso.objects
        .filter(veiculo__aluno=request.aluno, data_entrada__year=ano, data_entrada__month=mes)
        .select_related("veiculo")
        .order_by("data_entrada")
    )
    return resposta_csv(registros, f"relatorio_{ano}_{mes:02d}.csv", COLUNAS_ALUNO)


TIPO_FORM_PARA_MODELO = {
    "automovel": TipoVeiculo.CARRO,
    "motocicleta": TipoVeiculo.MOTO,
}
TIPO_MODELO_PARA_FORM = {v: k for k, v in TIPO_FORM_PARA_MODELO.items()}


def _ler_form_veiculo(request):
    """Lê e valida o formulário de veículo do aluno (cadastro e edição). Retorna (valores, seguro, erros)."""
    valores = {
        "tipo_veiculo": request.POST.get("tipo_veiculo", "automovel"),
        "placa": re.sub(r"[^A-Za-z0-9]", "", request.POST.get("placa", "")).upper(),
        "modelo_ano": request.POST.get("modelo_ano", "").strip(),
    }
    seguro_ativo = request.POST.get("seguro_ativo") == "on"

    erros = []
    if not valores["placa"]:
        erros.append("Informe a placa do veículo.")
    elif not PLACA_REGEX.match(valores["placa"]):
        erros.append("Placa inválida. Use o formato Mercosul: 4 letras e 3 números, ex: ABC1D23.")

    if not valores["modelo_ano"]:
        erros.append("Informe o modelo e ano do veículo.")

    return valores, seguro_ativo, erros


@aluno_required
def cadastro_veiculo_view(request):
    if request.method == "POST":
        valores, seguro_ativo, erros = _ler_form_veiculo(request)

        if not erros:
            try:
                with transaction.atomic():
                    Veiculo.objects.create(
                        placa=valores["placa"],
                        aluno=request.aluno,
                        tipo=TIPO_FORM_PARA_MODELO.get(valores["tipo_veiculo"], TipoVeiculo.CARRO),
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
def editar_veiculo_view(request, veiculo_id):
    """Aluno altera os dados do próprio veículo (RF13). A autorização é exclusiva do operador."""
    veiculo = get_object_or_404(Veiculo, pk=veiculo_id, aluno=request.aluno)

    try:
        VeiculoService.garantir_fora_do_estacionamento(veiculo)
    except OperacaoVeiculoNegada as e:
        messages.error(request, str(e))
        return redirect("meus-veiculos")

    contexto = {"aluno": request.aluno, "veiculo": veiculo, "editando": True}

    if request.method == "POST":
        valores, seguro_ativo, erros = _ler_form_veiculo(request)

        if not erros:
            veiculo.placa = valores["placa"]
            veiculo.tipo = TIPO_FORM_PARA_MODELO.get(valores["tipo_veiculo"], TipoVeiculo.CARRO)
            veiculo.modelo = valores["modelo_ano"]
            veiculo.seguro_ativo = seguro_ativo
            try:
                with transaction.atomic():
                    veiculo.save(update_fields=["placa", "tipo", "modelo", "seguro_ativo"])
            except IntegrityError:
                erros.append("Já existe um veículo cadastrado com essa placa.")
            else:
                messages.success(request, "Veículo atualizado com sucesso.")
                return redirect("meus-veiculos")

        contexto.update(erros=erros, valores=valores, seguro_ativo=seguro_ativo)
        return render(request, "veiculo/cadastro_veiculo.html", contexto, status=400)

    contexto.update(
        valores={
            "tipo_veiculo": TIPO_MODELO_PARA_FORM.get(veiculo.tipo, "automovel"),
            "placa": veiculo.placa,
            "modelo_ano": veiculo.modelo,
        },
        seguro_ativo=veiculo.seguro_ativo,
    )
    return render(request, "veiculo/cadastro_veiculo.html", contexto)


@aluno_required
@require_POST
def excluir_veiculo_view(request, veiculo_id):
    veiculo = get_object_or_404(Veiculo, pk=veiculo_id, aluno=request.aluno)
    try:
        VeiculoService.excluir(veiculo)
    except OperacaoVeiculoNegada as e:
        messages.error(request, str(e))
    else:
        messages.success(request, "Veículo removido com sucesso.")
    return redirect("meus-veiculos")


@aluno_required
def meus_veiculos_view(request):
    veiculos = Veiculo.objects.filter(aluno=request.aluno).order_by("-id")
    return render(request, "veiculo/meus_veiculos.html", {"aluno": request.aluno, "veiculos": veiculos})
