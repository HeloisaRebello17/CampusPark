from django.db import models
from apps.campuspark_veiculo.models import Veiculo
from apps.campuspark_usuario.models import Operador



class StatusAcesso(models.TextChoices):
    DENTRO = "DENTRO", "Dentro do estacionamento"
    FINALIZADO = "FINALIZADO", "Saída registrada"
    NEGADO = "NEGADO", "Acesso negado"

class RegistroAcesso(models.Model):
    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name="registros")
    operador = models.ForeignKey(Operador, on_delete=models.SET_NULL, null=True, blank=True)
    data_entrada = models.DateTimeField(auto_now_add=True)
    data_saida = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=StatusAcesso.choices, default=StatusAcesso.DENTRO)

    class Meta:
        indexes = [models.Index(fields=["veiculo", "status"])]

    def __str__(self):
        return f"{self.veiculo.placa} - {self.status}"