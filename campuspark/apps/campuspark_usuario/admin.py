
from django.contrib import admin
from .models import Aluno, Operador, TipoOperador

@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ("matricula", "nome_completo", "ativo", "data_criacao")
    search_fields = ("matricula", "nome_completo", "cpf")
    list_filter = ("ativo",)

@admin.register(Operador)
class OperadorAdmin(admin.ModelAdmin):
    list_display = ("nome_completo", "tipo_operador", "email")
    search_fields = ("nome_completo", "cpf")

admin.site.register(TipoOperador)