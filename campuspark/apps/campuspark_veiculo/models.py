from django.db import models


class TipoVeiculo(models.TextChoices):
    CARRO = "carro", "Carro"
    MOTO = "moto", "Moto"
    OUTRO = "outro", "Outro"


class Veiculo(models.Model):
    aluno = models.ForeignKey("campuspark_usuario.Aluno", on_delete=models.CASCADE, related_name="veiculos")
    placa = models.CharField(max_length=7, unique=True)
    renavam = models.CharField(max_length=11, unique=True, blank=True, null=True)
    tipo = models.CharField(max_length=20, choices=TipoVeiculo.choices)
    fabricante = models.CharField(max_length=30, blank=True)
    modelo = models.CharField(max_length=30, blank=True)
    cor = models.CharField(max_length=20, blank=True)
    tag_rfid = models.CharField(max_length=30, unique=True)
    autorizado = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.placa} - {self.aluno}"
