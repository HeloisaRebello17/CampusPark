from django.contrib import admin
from .models import RegistroAcesso, ConfiguracaoEstacionamento, AberturaCancela

@admin.register(RegistroAcesso)
class RegistroAcessoAdmin(admin.ModelAdmin):
    list_display = ("placa_exibicao", "nome_exibicao", "status", "liberacao_manual", "data_entrada", "data_saida")
    list_filter = ("status", "liberacao_manual")
    search_fields = ("veiculo__placa", "placa_visitante", "nome_visitante", "veiculo__aluno__nome_completo")


@admin.register(ConfiguracaoEstacionamento)
class ConfiguracaoEstacionamentoAdmin(admin.ModelAdmin):
    list_display = ("vagas_carro", "vagas_moto", "exigir_face_saida", "atualizado_em")


@admin.register(AberturaCancela)
class AberturaCancelaAdmin(admin.ModelAdmin):
    list_display = ("data_hora", "tipo", "sentido", "placa_exibicao", "operador", "motivo")
    list_filter = ("tipo", "sentido")
