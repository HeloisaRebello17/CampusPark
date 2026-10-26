from django.db.models import ProtectedError

from apps.campuspark_acesso.models import RegistroAcesso, StatusAcesso


class OperacaoVeiculoNegada(Exception):
    pass


class VeiculoService:

    @staticmethod
    def esta_no_estacionamento(veiculo) -> bool:
        return RegistroAcesso.objects.filter(veiculo=veiculo, status=StatusAcesso.DENTRO).exists()

    @staticmethod
    def garantir_fora_do_estacionamento(veiculo) -> None:
        """Com uma entrada em aberto o veículo não pode ser alterado nem removido: mudar placa/tipo
        quebraria a contagem de vagas e a saída (RN05/RN06)."""
        if VeiculoService.esta_no_estacionamento(veiculo):
            raise OperacaoVeiculoNegada(
                "Este veículo está dentro do estacionamento. Registre a saída antes de alterá-lo ou removê-lo."
            )

    @staticmethod
    def excluir(veiculo) -> None:
        VeiculoService.garantir_fora_do_estacionamento(veiculo)
        try:
            veiculo.delete()
        except ProtectedError:
            # RegistroAcesso usa PROTECT: o histórico de acessos (RF10) não pode ser perdido.
            raise OperacaoVeiculoNegada(
                "Este veículo possui histórico de acessos e não pode ser excluído. "
                "Para impedir novas entradas, peça à segurança para bloqueá-lo."
            )

    @staticmethod
    def alterar_autorizacao(veiculo, autorizado: bool) -> None:
        """Autorizar/bloquear é exclusivo do operador (RF13, RF15). Bloquear impede novas entradas;
        um veículo já dentro continua podendo sair."""
        veiculo.autorizado = autorizado
        veiculo.save(update_fields=["autorizado"])
