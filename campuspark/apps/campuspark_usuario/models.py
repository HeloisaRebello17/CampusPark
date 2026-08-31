# models.py
# Histórico de entrada e saída de veículos.
from django.db import models

class HistoricoEntrada(models.Model):
    veiculo = models.ForeignKey("campuspark_veiculo.Veiculo", on_delete=models.CASCADE)
    data_entrada = models.DateTimeField(auto_now_add=True)

class HistoricoSaida(models.Model):
    veiculo = models.ForeignKey("campuspark_veiculo.Veiculo", on_delete=models.CASCADE)
    data_saida = models.DateTimeField(auto_now_add=True)

class Aluno(models.Model):
    matricula = models.CharField(max_length=7, unique=True)
    cpf = models.CharField(max_length=11, unique=True)
    nome_completo = models.CharField(max_length=200)
    email_institucional = models.EmailField(max_length=64)
    senha_hash = models.CharField(max_length=255)
    ativo = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.matricula} - {self.nome_completo}"


class TipoOperador(models.Model):
    descricao = models.CharField(max_length=30)

    def __str__(self):
        return self.descricao


class Operador(models.Model):
    tipo_operador = models.ForeignKey(TipoOperador, on_delete=models.PROTECT)
    cpf = models.CharField(max_length=11, unique=True)
    nome_completo = models.CharField(max_length=200)
    email = models.EmailField(max_length=255)
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome_completo