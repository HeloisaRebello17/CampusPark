# models.py
# Histórico de entrada e saída de veículos.
from django.db import models

class HistoricoEntrada(models.Model):
    carro = models.ForeignKey("veiculos.Carro", on_delete=models.CASCADE)
    data_entrada = models.DateTimeField(auto_now_add=True)

class HistoricoSaida(models.Model):
    carro = models.ForeignKey("veiculos.Carro", on_delete=models.CASCADE)
    data_saida = models.DateTimeField(auto_now_add=True)
