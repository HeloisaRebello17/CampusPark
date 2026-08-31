from django.contrib import admin
from .models import Biometria


@admin.register(Biometria)
class BiometriaAdmin(admin.ModelAdmin):
    list_display = ("aluno", "modelo_ia", "ativo", "data_criacao")
    list_filter = ("ativo", "modelo_ia")
    search_fields = ("aluno__matricula", "aluno__nome_completo")
