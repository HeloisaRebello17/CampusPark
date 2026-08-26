from django.db import models

class Veiculo(models.Model):
    placa = models.CharField(max_length=7, unique=True)
    aluno = models.ForeignKey("campuspark_usuario.Aluno", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.placa} - {self.aluno}"
