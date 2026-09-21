from django.utils import timezone
from apps.campuspark_veiculo.models import Veiculo, TipoVeiculo
from integrations.cancela import Cancela
from .models import RegistroAcesso, StatusAcesso, ConfiguracaoEstacionamento

class AcessoNegado(Exception):
    pass

class AcessoService:

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

        Cancela().abrir(motivo=f"Entrada liberada para {veiculo.placa}.")
        return RegistroAcesso.objects.create(veiculo=veiculo, operador=operador)

    @staticmethod
    def registrar_saida(tag_rfid: str) -> RegistroAcesso:
        registro = RegistroAcesso.objects.filter(
            veiculo__tag_rfid=tag_rfid, status=StatusAcesso.DENTRO
        ).order_by("-data_entrada").first()

        if not registro:
            raise AcessoNegado("Não há entrada em aberto para esta TAG.")

        registro.data_saida = timezone.now()
        registro.status = StatusAcesso.FINALIZADO
        registro.save(update_fields=["data_saida", "status"])
        Cancela().abrir(motivo=f"Saída liberada para {registro.veiculo.placa}.")
        return registro