from django.http import JsonResponse

class PerfilAccessMiddleware:
    ROTAS_ADMIN = ["/admin/"]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if any(request.path.startswith(r) for r in self.ROTAS_ADMIN):
            if request.user.is_authenticated and not request.user.is_staff:
                return JsonResponse({"erro": "Acesso restrito a administradores."}, status=403)
        return self.get_response(request)