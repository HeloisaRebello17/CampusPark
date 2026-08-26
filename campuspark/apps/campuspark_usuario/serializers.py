from rest_framework import serializers
from .models import Aluno, Operador, TipoOperador

class AlunoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aluno
        fields = ["id", "matricula", "cpf", "nome_completo", "email_institucional", "ativo", "data_criacao"]
        read_only_fields = ["id", "data_criacao"]

class TipoOperadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoOperador
        fields = ["id", "descricao"]

class OperadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Operador
        fields = ["id", "tipo_operador", "cpf", "nome_completo", "email", "data_criacao"]
        read_only_fields = ["id", "data_criacao"]