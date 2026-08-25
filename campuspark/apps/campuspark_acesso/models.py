# models.py
# Define as tabelas de alunos e operadores no banco de dados.
# Cada classe representa uma entidade (Aluno, Operador, TipoOperador).
from django.db import models

class Aluno(models.Model):
    matricula = models.CharField(max_length=7, unique=True)  # matrícula única
    nome = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
