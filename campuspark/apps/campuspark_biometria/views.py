# views.py
# Endpoints REST do reconhecimento facial:
#   POST /api/biometria/cadastro/    -> cadastra o(s) rosto(s) de um aluno
#   POST /api/biometria/reconhecer/  -> identifica um aluno a partir de uma foto

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.campuspark_usuario.models import Aluno
from .serializers import CadastroFacialSerializer, ReconhecimentoFacialSerializer
from .services import BiometriaService, RostoNaoDetectado


class CadastroFacialView(APIView):
    """Recebe 1+ fotos de um aluno ja cadastrado e salva o(s) embedding(s) do rosto."""

    def post(self, request):
        serializer = CadastroFacialSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data

        aluno = None
        if dados.get("aluno_id"):
            aluno = Aluno.objects.filter(pk=dados["aluno_id"]).first()
        elif dados.get("matricula"):
            aluno = Aluno.objects.filter(matricula=dados["matricula"]).first()

        if aluno is None:
            return Response({"erro": "Aluno nao encontrado."}, status=status.HTTP_404_NOT_FOUND)

        try:
            total_salvo = BiometriaService.cadastrar(aluno, dados["imagens"])
        except RostoNaoDetectado as e:
            return Response({"erro": str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        return Response(
            {"aluno_id": aluno.id, "matricula": aluno.matricula, "amostras_salvas": total_salvo},
            status=status.HTTP_201_CREATED,
        )


class ReconhecimentoFacialView(APIView):
    """
    Recebe 1 foto (frame da camera da cancela ou da webcam de teste) e tenta
    identificar o aluno. Sempre responde 200 -- 'reconhecido: false' NAO e erro,
    e um resultado esperado (rosto nao bateu com ninguem cadastrado).
    """

    def post(self, request):
        serializer = ReconhecimentoFacialSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            aluno, score = BiometriaService.reconhecer(serializer.validated_data["imagem"])
        except RostoNaoDetectado as e:
            return Response({"erro": str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        if aluno is None:
            return Response({"reconhecido": False, "score": round(score, 4)}, status=status.HTTP_200_OK)

        return Response(
            {
                "reconhecido": True,
                "aluno_id": aluno.id,
                "matricula": aluno.matricula,
                "nome": aluno.nome_completo,
                "score": round(score, 4),
            },
            status=status.HTTP_200_OK,
        )
