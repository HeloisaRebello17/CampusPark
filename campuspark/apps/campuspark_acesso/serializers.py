from rest_framework import serializers
from .models import RegistroAcesso

class RegistroAcessoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroAcesso
        fields = ["id", "veiculo", "operador", "data_entrada", "data_saida", "status"]
        read_only_fields = ["id", "data_entrada"]