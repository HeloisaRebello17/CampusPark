# models.py
# Guarda o "vetor facial" (embedding) de cada aluno cadastrado.
# Não guardamos a foto em si, apenas os números que representam o rosto —
# isso deixa a comparação rápida e evita armazenar imagens sensíveis sem necessidade.

from django.db import models


class Biometria(models.Model):
    aluno = models.ForeignKey(
        "campuspark_usuario.Aluno",
        on_delete=models.CASCADE,
        related_name="biometrias",
    )
    embedding = models.BinaryField(
        help_text="Vetor numérico (float32) que representa o rosto, gerado pelo modelo SFace."
    )
    modelo_ia = models.CharField(
        max_length=50,
        default="sface_2021dec",
        help_text="Identifica qual modelo gerou o embedding, para não misturar vetores incompatíveis.",
    )
    ativo = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["aluno", "ativo"])]

    def __str__(self):
        return f"Biometria de {self.aluno.matricula} ({self.modelo_ia})"
