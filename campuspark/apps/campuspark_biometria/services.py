# services.py
# Camada de negocio do reconhecimento facial -- mesma logica do FacialRecognition
# (integrations/), so que aqui a gente lida com o mundo Django: arquivos enviados
# por HTTP, o Aluno do banco, e o cache do "motor" de reconhecimento entre requests.

import numpy as np
import cv2

from integrations.facial_recognition import FacialRecognition


class RostoNaoDetectado(Exception):
    """Nenhum rosto foi encontrado na imagem enviada."""
    pass


class BiometriaService:
    # instancia unica do motor de reconhecimento, compartilhada entre requests.
    # Carregar os modelos .onnx e os embeddings do banco tem um custo -- nao
    # faz sentido repetir isso a cada chamada da API, entao guardamos aqui.
    _engine = None

    @classmethod
    def _get_engine(cls) -> FacialRecognition:
        if cls._engine is None:
            cls._engine = FacialRecognition()
            cls._engine.carregar_cache()
        return cls._engine

    @staticmethod
    def _arquivo_para_frame(arquivo) -> np.ndarray:
        """Converte um arquivo enviado via multipart/form-data em um frame OpenCV."""
        dados = np.frombuffer(arquivo.read(), dtype=np.uint8)
        frame = cv2.imdecode(dados, cv2.IMREAD_COLOR)
        if frame is None:
            raise RostoNaoDetectado("Nao foi possivel ler a imagem enviada (arquivo invalido ou corrompido).")
        return frame

    @classmethod
    def cadastrar(cls, aluno, arquivos_imagem: list) -> int:
        """
        Recebe uma lista de arquivos de imagem (fotos do aluno) e salva um
        embedding para cada rosto detectado. Retorna quantas amostras foram salvas.
        """
        from .models import Biometria

        engine = cls._get_engine()
        salvos = 0

        for arquivo in arquivos_imagem:
            frame = cls._arquivo_para_frame(arquivo)
            face = engine.detectar(frame)
            if face is None:
                continue  # essa foto especifica nao tinha rosto detectavel, pula e segue nas outras

            embedding = engine.extrair_embedding(frame, face)
            if embedding is None:
                continue

            Biometria.objects.create(
                aluno=aluno,
                embedding=embedding.tobytes(),
                modelo_ia="sface_2021dec",
            )
            salvos += 1

        if salvos == 0:
            raise RostoNaoDetectado("Nenhum rosto foi detectado nas imagens enviadas.")

        # o aluno acabou de ganhar embeddings novos -- o cache em memoria precisa
        # ser atualizado, senao o reconhecimento so vai "ver" esse aluno depois
        # que o servidor reiniciar.
        engine.carregar_cache()
        return salvos

    @classmethod
    def reconhecer(cls, arquivo_imagem):
        """
        Recebe 1 arquivo de imagem (frame da camera) e tenta identificar o aluno.
        Retorna (aluno, score). 'aluno' vem None se nao bateu com ninguem.
        """
        engine = cls._get_engine()
        frame = cls._arquivo_para_frame(arquivo_imagem)
        return engine.reconhecer(frame)
