from django.utils import timezone
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

    @property
    def permanencia(self):
        """Tempo decorrido desde a entrada (até agora, ou até a saída se já finalizada)."""
        fim = self.data_saida or timezone.now()
        return fim - self.data_entrada
        


class ConfiguracaoEstacionamento(models.Model):
    """Capacidade máxima de vagas do estacionamento, por tipo de veículo."""

    vagas_carro = models.PositiveIntegerField(default=0)
    vagas_moto = models.PositiveIntegerField(default=0)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração do Estacionamento"
        verbose_name_plural = "Configuração do Estacionamento"

    def __str__(self):
        return f"{self.vagas_carro} vaga(s) carro / {self.vagas_moto} vaga(s) moto"

    @classmethod
    def obter(cls) -> "ConfiguracaoEstacionamento":
        config, _ = cls.objects.get_or_create(pk=1)
        return config


class TipoAbertura(models.TextChoices):
    AUTOMATICA = "AUTOMATICA", "Automática"
    MANUAL = "MANUAL", "Manual"


class SentidoAbertura(models.TextChoices):
    ENTRADA = "ENTRADA", "Entrada"
    SAIDA = "SAIDA", "Saída"


class AberturaCancela(models.Model):
    """Registro de cada vez que a cancela foi aberta: automática (TAG + rosto) ou manual (operador)."""

    tipo = models.CharField(max_length=10, choices=TipoAbertura.choices)
    sentido = models.CharField(max_length=7, choices=SentidoAbertura.choices)
    veiculo = models.ForeignKey(
        Veiculo, on_delete=models.SET_NULL, null=True, blank=True, related_name="aberturas_cancela"
    )
    registro = models.ForeignKey(
        RegistroAcesso, on_delete=models.SET_NULL, null=True, blank=True, related_name="aberturas"
    )
    operador = models.ForeignKey(
        Operador, on_delete=models.SET_NULL, null=True, blank=True, related_name="aberturas_cancela"
    )
    placa_informada = models.CharField(max_length=7, blank=True)
    motivo = models.CharField(max_length=255, blank=True)
    data_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data_hora"]
        verbose_name = "Abertura da cancela"
        verbose_name_plural = "Aberturas da cancela"

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.get_sentido_display()} - {self.data_hora:%d/%m/%Y %H:%M}"

    @property
    def placa_exibicao(self) -> str:
        if self.veiculo_id:
            return self.veiculo.placa
        return self.placa_informada or "-"
