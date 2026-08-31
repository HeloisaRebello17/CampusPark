# Uso:
#   python manage.py cadastrar_rosto 2024001
#   python manage.py cadastrar_rosto 2024001 --amostras 8
#
# Abre a webcam, mostra o rosto detectado em tempo real.
# ESPACO -> captura uma amostra do rosto atual
# ESC    -> cancela
#
# Tirar varias amostras (angulos/expressoes levemente diferentes) deixa o
# reconhecimento mais robusto do que uma unica foto.

from django.core.management.base import BaseCommand, CommandError
import cv2

from apps.campuspark_usuario.models import Aluno
from apps.campuspark_biometria.models import Biometria
from integrations.camera import Camera
from integrations.facial_recognition import FacialRecognition


class Command(BaseCommand):
    help = "Cadastra o rosto de um aluno a partir da webcam."

    def add_arguments(self, parser):
        parser.add_argument("matricula", type=str, help="Matricula do aluno ja cadastrado no sistema.")
        parser.add_argument("--amostras", type=int, default=5, help="Quantas capturas tirar (padrao: 5).")

    def handle(self, *args, **options):
        matricula = options["matricula"]
        n_amostras = options["amostras"]

        try:
            aluno = Aluno.objects.get(matricula=matricula)
        except Aluno.DoesNotExist:
            raise CommandError(f"Aluno com matricula '{matricula}' nao encontrado. Cadastre o aluno primeiro.")

        fr = FacialRecognition()
        embeddings = []

        self.stdout.write(self.style.NOTICE(
            f"Cadastrando rosto de {aluno.nome_completo}. "
            f"[ESPACO] captura  [ESC] cancela  -- meta: {n_amostras} amostras."
        ))

        with Camera() as cam:
            while len(embeddings) < n_amostras:
                frame = cam.capturar_frame()
                face = fr.detectar(frame)

                preview = frame.copy()
                if face is not None:
                    x, y, w, h = face[:4].astype(int)
                    cv2.rectangle(preview, (x, y), (x + w, y + h), (0, 200, 0), 2)

                cv2.putText(
                    preview,
                    f"Amostras: {len(embeddings)}/{n_amostras}  [ESPACO] capturar  [ESC] sair",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 200, 0), 1,
                )
                cv2.imshow("Cadastro facial", preview)
                key = cv2.waitKey(1) & 0xFF

                if key == 27:  # ESC
                    self.stdout.write(self.style.WARNING("Cadastro cancelado."))
                    break

                if key == 32 and face is not None:  # ESPACO
                    embedding = fr.extrair_embedding(frame, face)
                    if embedding is not None:
                        embeddings.append(embedding)
                        self.stdout.write(f"Amostra {len(embeddings)}/{n_amostras} capturada.")

        cv2.destroyAllWindows()

        if not embeddings:
            self.stdout.write(self.style.WARNING("Nenhuma amostra capturada. Nada foi salvo."))
            return

        for emb in embeddings:
            Biometria.objects.create(
                aluno=aluno,
                embedding=emb.tobytes(),
                modelo_ia="sface_2021dec",
            )

        self.stdout.write(self.style.SUCCESS(
            f"{len(embeddings)} amostra(s) salvas para {aluno.nome_completo} (matricula {matricula})."
        ))
