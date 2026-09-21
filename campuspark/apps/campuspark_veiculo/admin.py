from django.contrib import admin
from .models import Veiculo

@admin.register(Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display = ("placa", "tipo", "aluno", "tag_rfid", "autorizado")
    list_filter = ("tipo", "autorizado")
    search_fields = ("placa", "tag_rfid", "aluno__nome_completo")
