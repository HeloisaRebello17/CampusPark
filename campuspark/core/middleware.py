# middleware.py
# Middleware para segurança, logs e auditoria.
def log_request(get_response):
    def middleware(request):
        print(f"Requisição recebida: {request.path}")
        return get_response(request)
    return middleware
