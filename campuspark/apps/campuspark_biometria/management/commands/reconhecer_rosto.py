# Uso:
#   python manage.py reconhecer_rosto
#
# Abre a webcam e tenta reconhecer o rosto em tempo real, comparando com todos
# os alunos cadastrados. Mostra na tela o nome (se encontrado), o score de
# similaridade e o tempo gasto em milissegundos em cada tentativa -- e assim
# que voce confirma visualmente se esta dentro da meta de 2 segundos.
#
# ESC -> sai

from django.core.management.base import BaseCommand
import cv2
import time

from integrations.camera import Camera
from integrations.facial_recognition import FacialRecognition


class Command(BaseCommand):
    help = "Testa o reconhecimento facial em tempo real usando a webcam."

    def handle(self, *args, **options):
        fr = FacialRecognition()
        fr.carregar_cache()

        if len(fr._cache_alunos) == 0:
            self.stdout.write(self.style.WARNING(
                "Nenhum aluno com rosto cadastrado ainda. "
                "Rode 'python manage.py cadastrar_rosto <matricula>' primeiro."
            ))

        self.stdout.write(self.style.NOTICE("Reconhecimento iniciado. Pressione ESC para sair."))

        with Camera() as cam:
            while True:
                inicio = time.time()
                frame = cam.capturar_frame()
                aluno, score = fr.reconhecer(frame)
                elapsed_ms = (time.time() - inicio) * 1000

                if aluno:
                    label = f"{aluno.nome_completo} ({score:.2f})"
                    cor = (0, 200, 0)
                else:
                    label = f"Nao identificado ({score:.2f})"
                    cor = (0, 0, 220)

                cv2.putText(frame, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor, 2)
                cv2.putText(frame, f"{elapsed_ms:.0f} ms", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                cv2.imshow("Reconhecimento facial", frame)

                if cv2.waitKey(1) & 0xFF == 27:
                    break

        cv2.destroyAllWindows()
