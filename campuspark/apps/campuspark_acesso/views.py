from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import AcessoService, AcessoNegado
from .serializers import RegistroAcessoSerializer

class EntradaView(APIView):
    def post(self, request):
        tag = request.data.get("tag_rfid")
        try:
            registro = AcessoService.validar_entrada(tag)
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