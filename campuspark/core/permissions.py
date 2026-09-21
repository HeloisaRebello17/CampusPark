from functools import wraps

from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from rest_framework.permissions import BasePermission


class EhAdministrador(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)


def get_operador_logado(request):
    """Retorna o Operador da sessão atual (porteiro ou administrador), ou None — RNF14."""
    from apps.campuspark_usuario.models import Operador

    operador_id = request.session.get("operador_id")
    if not operador_id:
        return None
    return Operador.objects.select_related("tipo_operador").filter(pk=operador_id).first()


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