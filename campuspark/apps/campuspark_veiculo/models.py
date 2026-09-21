from django.db import models

class Veiculo(models.Model):
    class TipoVeiculo(models.TextChoices):
        AUTOMOVEL = "AUTOMOVEL", "Automóvel"
        MOTOCICLETA = "MOTOCICLETA", "Motocicleta"

    placa = models.CharField(max_length=7, unique=True)
    aluno = models.ForeignKey("campuspark_usuario.Aluno", on_delete=models.CASCADE)
    tipo_veiculo = models.CharField(max_length=11, choices=TipoVeiculo.choices, default=TipoVeiculo.AUTOMOVEL)
    modelo_ano = models.CharField(max_length=100, blank=True)
    seguro_ativo = models.BooleanField(default=False)
    autorizado = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.placa} - {self.aluno}"
