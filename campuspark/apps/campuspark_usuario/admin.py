
from django import forms
from django.contrib import admin
from django.contrib.auth.hashers import make_password
from .models import Aluno, Operador, TipoOperador

@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ("matricula", "nome_completo", "ativo", "data_criacao")
    search_fields = ("matricula", "nome_completo", "cpf")
    list_filter = ("ativo",)


class OperadorAdminForm(forms.ModelForm):
    senha = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput,
        required=False,
        help_text="Preencha para definir/alterar a senha de login do operador.",
    )

    class Meta:
        model = Operador
        exclude = ["senha_hash"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk is None:
            self.fields["senha"].required = True

    def save(self, commit=True):
        operador = super().save(commit=False)
        senha = self.cleaned_data.get("senha")
        if senha:
            operador.senha_hash = make_password(senha)
        if commit:
            operador.save()
        return operador


@admin.register(Operador)
class OperadorAdmin(admin.ModelAdmin):
    form = OperadorAdminForm
    list_display = ("nome_completo", "tipo_operador", "cpf", "email", "ativo")
    list_filter = ("tipo_operador", "ativo")
    search_fields = ("nome_completo", "cpf")

admin.site.register(TipoOperador)