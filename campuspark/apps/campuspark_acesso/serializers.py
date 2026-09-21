from rest_framework import serializers
from .models import RegistroAcesso

class RegistroAcessoSerializer(serializers.ModelSerializer):
    permanencia_segundos = serializers.SerializerMethodField()

    class Meta:
        model = RegistroAcesso
        fields = ["id", "veiculo", "operador", "data_entrada", "data_saida", "status", "permanencia_segundos"]
        read_only_fields = ["id", "data_entrada"]

    def get_permanencia_segundos(self, obj):
        return int(obj.permanencia.total_seconds())