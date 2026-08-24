# models.py
# Define a tabela de veículos vinculados a alunos.
from django.db import models

class Carro(models.Model):
    placa = models.CharField(max_length=7, unique=True)  # placa única
    aluno = models.ForeignKey("usuarios.Aluno", on_delete=models.CASCADE)
