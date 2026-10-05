from django.db import transaction
from django.utils import timezone
from apps.campuspark_veiculo.models import Veiculo, TipoVeiculo
from integrations.cancela import Cancela
from .models import (
    RegistroAcesso, StatusAcesso, ConfiguracaoEstacionamento,
    AberturaCancela, TipoAbertura, SentidoAbertura,
)

class AcessoNegado(Exception):
    pass


def _formatar_data(dt) -> str:
    if dt is None:
        return "-"
    if timezone.is_aware(dt):
        dt = timezone.localtime(dt)
    return dt.strftime("%d/%m/%Y %H:%M:%S")


def anunciar_rosto(aluno) -> None:
    """Mensagem de terminal simulando a leitura do rosto (reconhecimento facial)."""
    print(f"[RECONHECIMENTO FACIAL] Rosto reconhecido: {aluno.nome_completo} (matricula {aluno.matricula})")


def anunciar_acesso(registro: RegistroAcesso, sentido: str) -> None:
    """Mensagem de terminal simulando a tela de 'acesso autorizado'."""
    rotulo = "Entrada" if sentido == SentidoAbertura.ENTRADA else "Saida"
    print(
        f"[ACESSO AUTORIZADO] {rotulo} | Placa {registro.veiculo.placa} | "
        f"Entrada: {_formatar_data(registro.data_entrada)} | "
        f"Saida: {_formatar_data(registro.data_saida)}"
    )


class AcessoService:

    @staticmethod
    def _abrir_cancela(tipo, sentido, motivo, veiculo=None, registro=None,
                       operador=None, placa_informada="", mensagem_console=None) -> AberturaCancela:
        """Grava o registro da abertura e só então aciona a cancela.
        Sempre chamado dentro de transaction.atomic(): se a cancela falhar, nada fica gravado."""
        abertura = AberturaCancela.objects.create(
            tipo=tipo, sentido=sentido, veiculo=veiculo, registro=registro,
            operador=operador, placa_informada=placa_informada, motivo=motivo,
        )
        Cancela().abrir(motivo=mensagem_console or motivo)
        return abertura

    @staticmethod
    def validar_entrada(tag_rfid: str, aluno_reconhecido=None, operador=None) -> RegistroAcesso:
        try:
            veiculo = Veiculo.objects.select_related("aluno").get(tag_rfid=tag_rfid)
        except Veiculo.DoesNotExist:
            raise AcessoNegado("TAG não encontrada no sistema.")

        if not veiculo.autorizado or not veiculo.aluno.ativo:
            raise AcessoNegado("Veículo ou aluno não autorizado.")

        if aluno_reconhecido is not None and aluno_reconhecido.id != veiculo.aluno_id:
            raise AcessoNegado("O rosto reconhecido não corresponde ao aluno vinculado a esta TAG.")

        ja_dentro = RegistroAcesso.objects.filter(
            veiculo=veiculo, status=StatusAcesso.DENTRO
        ).exists()
        if ja_dentro:
            raise AcessoNegado("Este veículo já possui uma entrada em aberto.")

        config = ConfiguracaoEstacionamento.obter()
        capacidade = None
        if veiculo.tipo == TipoVeiculo.CARRO:
            capacidade = config.vagas_carro
        elif veiculo.tipo == TipoVeiculo.MOTO:
            capacidade = config.vagas_moto

        if capacidade is not None:
            ocupadas = RegistroAcesso.objects.filter(
                status=StatusAcesso.DENTRO, veiculo__tipo=veiculo.tipo
            ).count()
            if ocupadas >= capacidade:
                raise AcessoNegado("Não há vagas disponíveis para este tipo de veículo.")

        with transaction.atomic():
            registro = RegistroAcesso.objects.create(veiculo=veiculo, operador=operador)
            AcessoService._abrir_cancela(
                TipoAbertura.AUTOMATICA, SentidoAbertura.ENTRADA,
                motivo=f"Entrada liberada para {veiculo.placa}.",
                veiculo=veiculo, registro=registro, operador=operador,
            )
        return registro

    @staticmethod
    def registrar_saida(tag_rfid: str) -> RegistroAcesso:
        registro = RegistroAcesso.objects.select_related("veiculo").filter(
            veiculo__tag_rfid=tag_rfid, status=StatusAcesso.DENTRO
        ).order_by("-data_entrada").first()

        if not registro:
            raise AcessoNegado("Não há entrada em aberto para esta TAG.")

        with transaction.atomic():
            registro.data_saida = timezone.now()
            registro.status = StatusAcesso.FINALIZADO
            registro.save(update_fields=["data_saida", "status"])
            AcessoService._abrir_cancela(
                TipoAbertura.AUTOMATICA, SentidoAbertura.SAIDA,
                motivo=f"Saída liberada para {registro.veiculo.placa}.",
                veiculo=registro.veiculo, registro=registro,
            )
        return registro

    @staticmethod
    def liberar_manual(operador, sentido: str, motivo: str, placa: str = "") -> AberturaCancela:
        """Abertura manual da cancela por um operador logado. Só abre e registra (quem, quando, motivo);
        não cria nem finaliza RegistroAcesso."""
        motivo = (motivo or "").strip()
        placa = (placa or "").strip().upper()

        if operador is None:
            raise AcessoNegado("A liberação manual exige um operador autenticado.")
        if sentido not in SentidoAbertura.values:
            raise AcessoNegado("Sentido inválido. Escolha entrada ou saída.")
        if not motivo:
            raise AcessoNegado("Informe o motivo da liberação manual.")
        if len(motivo) > 255:
            raise AcessoNegado("O motivo deve ter no máximo 255 caracteres.")
        if len(placa) > 7:
            raise AcessoNegado("Placa inválida: use no máximo 7 caracteres.")

        veiculo = Veiculo.objects.filter(placa=placa).first() if placa else None

        with transaction.atomic():
            return AcessoService._abrir_cancela(
                TipoAbertura.MANUAL, sentido, motivo=motivo,
                veiculo=veiculo, operador=operador, placa_informada=placa,
                mensagem_console=f"Liberação manual por {operador.nome_completo}: {motivo}",
            )
