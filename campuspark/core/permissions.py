import hmac
from functools import wraps

from django.conf import settings
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from rest_framework.authentication import CSRFCheck
from rest_framework.permissions import SAFE_METHODS, BasePermission


def get_operador_logado(request):
    """Retorna o Operador ativo da sessão atual (porteiro ou administrador), ou None — RNF14.
    Um operador desativado perde o acesso na próxima requisição, mesmo com a sessão aberta."""
    from apps.campuspark_usuario.models import Operador

    operador_id = request.session.get("operador_id")
    if not operador_id:
        return None
    operador = Operador.objects.select_related("tipo_operador").filter(pk=operador_id, ativo=True).first()
    if operador is None:
        request.session.pop("operador_id", None)
    return operador


def operador_login_required(view_func):
    """Exige que um Operador (porteiro ou administrador) esteja autenticado — RNF14."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        operador = get_operador_logado(request)
        if operador is None:
            return redirect("operador-login")
        request.operador = operador
        return view_func(request, *args, **kwargs)

    return wrapper


def administrador_required(view_func):
    """Exige que o Operador autenticado seja do tipo Administrador — RNF14, RF15."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        operador = get_operador_logado(request)
        if operador is None:
            return redirect("operador-login")
        if not operador.is_administrador:
            return HttpResponseForbidden("Acesso restrito a administradores.")
        request.operador = operador
        return view_func(request, *args, **kwargs)

    return wrapper


# --- Permissões da API REST (RNF01, RNF14) ---
# O login do operador fica na sessão ("operador_id"), fora do auth do Django; por isso as
# permissões abaixo leem a sessão direto. Como as APIViews do DRF são isentas de CSRF, a
# checagem de CSRF é refeita aqui para requisições que alteram dados.

def _csrf_valido(request) -> bool:
    if request.method in SAFE_METHODS:
        return True
    check = CSRFCheck(lambda req: None)
    django_request = request._request
    check.process_request(django_request)
    return check.process_view(django_request, None, (), {}) is None


def _operador_da_api(request):
    operador = get_operador_logado(request)
    if operador is None or not _csrf_valido(request):
        return None
    return operador


class OperadorAutenticado(BasePermission):
    """Porteiro ou administrador logado (sessão + CSRF)."""

    message = "Faça login como operador para acessar este recurso."

    def has_permission(self, request, view):
        return _operador_da_api(request) is not None


class AdministradorAutenticado(BasePermission):
    """Operador do tipo Administrador logado, ou usuário staff do Django Admin."""

    message = "Acesso restrito a administradores."

    def has_permission(self, request, view):
        if request.user and request.user.is_staff:
            return True
        operador = _operador_da_api(request)
        return operador is not None and operador.is_administrador


class DispositivoAutorizado(BasePermission):
    """Equipamentos do estacionamento (cancela, leitor RFID, câmera) identificados pelo header
    X-API-Key == CAMPUSPARK_API_KEY. Sem a variável configurada, nenhum dispositivo é aceito."""

    message = "Chave de API ausente ou inválida."

    def has_permission(self, request, view):
        chave_esperada = settings.CAMPUSPARK_API_KEY
        chave_enviada = request.headers.get("X-API-Key", "")
        return bool(chave_esperada) and hmac.compare_digest(chave_enviada.encode(), chave_esperada.encode())
