from django.contrib import admin
from .models import RegistroAcesso

@admin.register(RegistroAcesso)
class RegistroAcessoAdmin(admin.ModelAdmin):
    list_display = ("veiculo", "status", "data_entrada", "data_saida")
    list_filter = ("status",)