# Uso:
#   python manage.py simular_acesso <TAG_RFID> --matricula <MATRICULA>          (entrada)
#   python manage.py simular_acesso <TAG_RFID> --saida                          (saida)
#
# Simula o momento em que o rosto e lido e a cancela abre: mostra no terminal o
# reconhecimento do aluno, a abertura da cancela e o resumo do acesso autorizado
# (placa, data de entrada e de saida). Se o acesso for negado, mostra o motivo.

from django.core.management.base import BaseCommand, CommandError

from apps.campuspark_usuario.models import Aluno
from apps.campuspark_acesso.models import SentidoAbertura
from apps.campuspark_acesso.services import (
    AcessoService, AcessoNegado, anunciar_rosto, anunciar_acesso,
)


class Command(BaseCommand):
    help = "Simula a leitura da TAG + rosto e a liberacao automatica da cancela."

    def add_arguments(self, parser):
        parser.add_argument("tag_rfid", help="TAG RFID do veiculo.")
        parser.add_argument("--matricula", help="Matricula do aluno 'reconhecido pelo rosto' (so na entrada).")
        parser.add_argument("--saida", action="store_true", help="Simula a saida em vez da entrada.")

    def handle(self, *args, **options):
        tag = options["tag_rfid"]
        saida = options["saida"]
        aluno = None

        if options["matricula"] and not saida:
            aluno = Aluno.objects.filter(matricula=options["matricula"]).first()
            if aluno is None:
                raise CommandError(f"Aluno com matricula {options['matricula']} nao encontrado.")
            anunciar_rosto(aluno)

        try:
            if saida:
                registro = AcessoService.registrar_saida(tag)
                sentido = SentidoAbertura.SAIDA
            else:
                registro = AcessoService.validar_entrada(tag, aluno_reconhecido=aluno)
                sentido = SentidoAbertura.ENTRADA
        except AcessoNegado as exc:
            self.stdout.write(self.style.ERROR(f"[ACESSO NEGADO] {exc}"))
            return

        anunciar_acesso(registro, sentido)
