import re

from django.db import transaction
from django.utils import timezone
from apps.campuspark_veiculo.models import Veiculo, TipoVeiculo
from apps.campuspark_veiculo.validators import PLACA_REGEX
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
        f"[ACESSO AUTORIZADO] {rotulo} | Placa {registro.placa_exibicao} | "
        f"Entrada: {_formatar_data(registro.data_entrada)} | "
        f"Saida: {_formatar_data(registro.data_saida)}"
    )


def normalizar_placa(texto: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", texto or "").upper()


def vagas_ocupadas(tipo) -> int:
    """Veículos dentro do estacionamento por tipo, cadastrados e visitantes."""
    return RegistroAcesso.objects.filter(RegistroAcesso.q_tipo(tipo), status=StatusAcesso.DENTRO).count()


def _garantir_vaga(tipo) -> None:
    config = ConfiguracaoEstacionamento.obter()
    capacidade = {TipoVeiculo.CARRO: config.vagas_carro, TipoVeiculo.MOTO: config.vagas_moto}.get(tipo)
    if capacidade is not None and vagas_ocupadas(tipo) >= capacidade:
        raise AcessoNegado("Não há vagas disponíveis para este tipo de veículo.")


def _validar_motivo(motivo: str) -> str:
    motivo = (motivo or "").strip()
    if not motivo:
        raise AcessoNegado("Informe o motivo da liberação manual.")
    if len(motivo) > 255:
        raise AcessoNegado("O motivo deve ter no máximo 255 caracteres.")
    return motivo


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

        _garantir_vaga(veiculo.tipo)

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
    def consultar_placa(placa: str):
        """Usado pela tela de entrada manual: diz se a placa é de um veículo cadastrado.
        Retorna (placa_normalizada, veiculo_ou_None)."""
        placa = normalizar_placa(placa)
        if not PLACA_REGEX.match(placa):
            raise AcessoNegado("Placa inválida. Use o formato ABC1234 ou ABC1D23.")
        return placa, Veiculo.objects.select_related("aluno").filter(placa=placa).first()

    @staticmethod
    def entrada_manual(operador, placa: str, motivo: str, tipo: str = "",
                       nome: str = "", documento: str = ""):
        """Entrada liberada pelo operador quando a TAG/rosto não funcionam ou o veículo não tem
        cadastro (visitante). Cria o RegistroAcesso (conta vaga, aparece no histórico) e abre a cancela.

        - Veículo cadastrado: entra mesmo bloqueado/aluno inativo, mas o motivo registra isso.
        - Visitante: exige tipo do veículo, nome e documento do motorista.
        - Em ambos os casos valem a lotação (sem vaga, não entra) e RN05 (já dentro, não entra).
        Retorna (registro, aviso) — aviso é preenchido quando o veículo estava bloqueado."""
        if operador is None:
            raise AcessoNegado("A liberação manual exige um operador autenticado.")
        motivo = _validar_motivo(motivo)
        placa, veiculo = AcessoService.consultar_placa(placa)

        if RegistroAcesso.objects.filter(RegistroAcesso.q_placa(placa), status=StatusAcesso.DENTRO).exists():
            raise AcessoNegado("Este veículo já possui uma entrada em aberto.")

        aviso = ""
        dados = {"operador": operador, "liberacao_manual": True}
        if veiculo is not None:
            if not veiculo.autorizado or not veiculo.aluno.ativo:
                aviso = "Atenção: o veículo está bloqueado ou o aluno está inativo. A liberação foi registrada."
                motivo = f"{motivo} [liberado com cadastro bloqueado/inativo]"[:255]
            tipo = veiculo.tipo
            dados["veiculo"] = veiculo
        else:
            nome = (nome or "").strip()
            documento = re.sub(r"[^A-Za-z0-9]", "", documento or "").upper()
            if tipo not in TipoVeiculo.values:
                raise AcessoNegado("Selecione o tipo do veículo do visitante.")
            if not nome:
                raise AcessoNegado("Informe o nome do motorista visitante.")
            if len(nome) > 200:
                raise AcessoNegado("O nome deve ter no máximo 200 caracteres.")
            if not 5 <= len(documento) <= 20:
                raise AcessoNegado("Informe o CPF ou RG do motorista visitante.")
            dados.update(
                placa_visitante=placa, tipo_visitante=tipo,
                nome_visitante=nome, documento_visitante=documento,
            )

        _garantir_vaga(tipo)

        with transaction.atomic():
            registro = RegistroAcesso.objects.create(motivo=motivo, **dados)
            AcessoService._abrir_cancela(
                TipoAbertura.MANUAL, SentidoAbertura.ENTRADA, motivo=motivo,
                veiculo=veiculo, registro=registro, operador=operador, placa_informada=placa,
                mensagem_console=f"Entrada manual de {placa} por {operador.nome_completo}: {motivo}",
            )
        return registro, aviso

    @staticmethod
    def saida_manual(operador, registro_id, motivo: str = "") -> RegistroAcesso:
        """Saída registrada pelo operador (visitante, ou TAG que não leu na saída)."""
        if operador is None:
            raise AcessoNegado("A liberação manual exige um operador autenticado.")
        motivo = (motivo or "").strip() or "Saída registrada manualmente."
        if len(motivo) > 255:
            raise AcessoNegado("O motivo deve ter no máximo 255 caracteres.")

        with transaction.atomic():
            registro = (
                RegistroAcesso.objects.select_for_update()
                .filter(pk=registro_id, status=StatusAcesso.DENTRO).first()
            )
            if registro is None:
                raise AcessoNegado("Não há entrada em aberto para este registro.")
            registro.data_saida = timezone.now()
            registro.status = StatusAcesso.FINALIZADO
            registro.save(update_fields=["data_saida", "status"])
            AcessoService._abrir_cancela(
                TipoAbertura.MANUAL, SentidoAbertura.SAIDA, motivo=motivo,
                veiculo=registro.veiculo, registro=registro, operador=operador,
                placa_informada=registro.placa_exibicao,
                mensagem_console=f"Saída manual de {registro.placa_exibicao} por {operador.nome_completo}: {motivo}",
            )
        return registro

    @staticmethod
    def liberar_manual(operador, sentido: str, motivo: str, placa: str = "") -> AberturaCancela:
        """Abertura avulsa da cancela (ex.: emergência). Só abre e registra (quem, quando, motivo);
        não cria nem finaliza RegistroAcesso — para isso use entrada_manual/saida_manual."""
        placa = (placa or "").strip().upper()

        if operador is None:
            raise AcessoNegado("A liberação manual exige um operador autenticado.")
        if sentido not in SentidoAbertura.values:
            raise AcessoNegado("Sentido inválido. Escolha entrada ou saída.")
        motivo = _validar_motivo(motivo)
        if len(placa) > 7:
            raise AcessoNegado("Placa inválida: use no máximo 7 caracteres.")

        veiculo = Veiculo.objects.filter(placa=placa).first() if placa else None

        with transaction.atomic():
            return AcessoService._abrir_cancela(
                TipoAbertura.MANUAL, sentido, motivo=motivo,
                veiculo=veiculo, operador=operador, placa_informada=placa,
                mensagem_console=f"Liberação manual por {operador.nome_completo}: {motivo}",
            )
