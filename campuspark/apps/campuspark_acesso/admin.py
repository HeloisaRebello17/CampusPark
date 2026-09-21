from django.contrib import admin
from .models import RegistroAcesso, ConfiguracaoEstacionamento

@admin.register(RegistroAcesso)
class RegistroAcessoAdmin(admin.ModelAdmin):
    list_display = ("veiculo", "status", "data_entrada", "data_saida")
    list_filter = ("status",)


@admin.register(ConfiguracaoEstacionamento)
class ConfiguracaoEstacionamentoAdmin(admin.ModelAdmin):
    list_display = ("vagas_carro", "vagas_moto", "atualizado_em")