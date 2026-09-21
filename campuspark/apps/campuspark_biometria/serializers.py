# serializers.py
# Validacao de entrada/saida dos endpoints de biometria facial.

from rest_framework import serializers


class CadastroFacialSerializer(serializers.Serializer):
    aluno_id = serializers.IntegerField(required=False)
    matricula = serializers.CharField(required=False)
    imagens = serializers.ListField(
        child=serializers.ImageField(),
        allow_empty=False,
        help_text="1 ou mais fotos do rosto do aluno.",
    )

    def validate(self, dados):
        if not dados.get("aluno_id") and not dados.get("matricula"):
            raise serializers.ValidationError("Informe 'aluno_id' ou 'matricula' para identificar o aluno.")
        return dados


class ReconhecimentoFacialSerializer(serializers.Serializer):
    imagem = serializers.ImageField(help_text="Frame/foto capturado pela camera para tentar reconhecer.")
