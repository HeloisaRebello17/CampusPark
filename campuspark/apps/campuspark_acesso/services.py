from django.utils import timezone
from apps.campuspark_veiculo.models import Veiculo
from .models import RegistroAcesso, StatusAcesso

class AcessoNegado(Exception):
    pass

class AcessoService:

    @staticmethod
    def validar_entrada(tag_rfid: str, operador=None) -> RegistroAcesso:
        try:
            veiculo = Veiculo.objects.select_related("aluno").get(tag_rfid=tag_rfid)
        except Veiculo.DoesNotExist:
            raise AcessoNegado("TAG não encontrada no sistema.")

        if not veiculo.autorizado or not veiculo.aluno.ativo:
            raise AcessoNegado("Veículo ou aluno não autorizado.")

        ja_dentro = RegistroAcesso.objects.filter(
            veiculo=veiculo, status=StatusAcesso.DENTRO
        ).exists()
        if ja_dentro:
            raise AcessoNegado("Este veículo já possui uma entrada em aberto.")

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
        return registro