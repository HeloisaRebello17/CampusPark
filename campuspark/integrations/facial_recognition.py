# facial_recognition.py
# Reconhecimento facial real, usando dois modelos leves embutidos no OpenCV:
#   - YuNet: detecta o rosto no frame (onde ele esta)
#   - SFace: transforma o rosto detectado em um vetor de 128 numeros (embedding)
#
# Nenhum dos dois exige compilador nem GPU. Ambos rodam bem em CPU e juntos
# levam poucas dezenas de milissegundos por frame -- bem abaixo do limite de 2s.
#
# Os arquivos .onnx dos modelos NAO estao no repositorio (sao baixados a parte,
# veja resources/models/README.md) porque sao arquivos binarios grandes demais
# para versionar como codigo.

import os

import numpy as np
import cv2
from django.conf import settings

MODEL_DIR = os.path.join(settings.BASE_DIR, "resources", "models")
DETECTOR_MODEL = os.path.join(MODEL_DIR, "face_detection_yunet_2023mar.onnx")
RECOGNIZER_MODEL = os.path.join(MODEL_DIR, "face_recognition_sface_2021dec.onnx")


class FacialRecognition:
    """
    Encapsula deteccao + extracao de embedding + comparacao contra o banco.

    match_threshold: quanto MAIOR, mais rigorosa a exigencia de semelhanca
    (0.36 e o valor de referencia usado pela documentacao do OpenCV para o SFace;
    ajuste para cima se estiver aceitando rostos parecidos demais, para baixo se
    estiver rejeitando o proprio aluno cadastrado).
    """

    def __init__(self, det_score_threshold: float = 0.9, match_threshold: float = 0.36):
        if not os.path.exists(DETECTOR_MODEL) or not os.path.exists(RECOGNIZER_MODEL):
            raise FileNotFoundError(
                "Modelos de reconhecimento facial nao encontrados em "
                f"'{MODEL_DIR}'. Veja resources/models/README.md para baixa-los."
            )

        self.detector = cv2.FaceDetectorYN_create(
            DETECTOR_MODEL, "", (320, 320), det_score_threshold, 0.3, 5000
        )
        self.recognizer = cv2.FaceRecognizerSF_create(RECOGNIZER_MODEL, "")
        self.match_threshold = match_threshold

        self._cache_embeddings = None  # np.ndarray shape (N, 128)
        self._cache_alunos = None      # lista de Aluno, mesma ordem do cache acima

    def detectar(self, frame):
        """Retorna a maior face encontrada no frame (array com bbox + landmarks) ou None."""
        h, w = frame.shape[:2]
        self.detector.setInputSize((w, h))
        _, faces = self.detector.detect(frame)
        if faces is None or len(faces) == 0:
            return None
        # se houver mais de um rosto no quadro, usa o maior (mais perto da camera)
        maior = max(faces, key=lambda f: f[2] * f[3])
        return maior

    def extrair_embedding(self, frame, face=None):
        """Alinha o rosto e extrai o vetor de 128 posicoes que o representa."""
        if face is None:
            face = self.detectar(frame)
        if face is None:
            return None
        aligned = self.recognizer.alignCrop(frame, face)
        feature = self.recognizer.feature(aligned)
        return feature.flatten().astype(np.float32)

    def carregar_cache(self):
        """Carrega em memoria os embeddings ativos cadastrados no banco (chame 1x ao iniciar)."""
        from apps.campuspark_biometria.models import Biometria

        registros = Biometria.objects.filter(ativo=True).select_related("aluno")
        embeddings, alunos = [], []
        for reg in registros:
            vetor = np.frombuffer(reg.embedding, dtype=np.float32)
            embeddings.append(vetor)
            alunos.append(reg.aluno)

        self._cache_embeddings = (
            np.array(embeddings, dtype=np.float32) if embeddings else np.empty((0, 128), dtype=np.float32)
        )
        self._cache_alunos = alunos

    def reconhecer(self, frame):
        """
        Compara o rosto do frame com os embeddings cadastrados no banco.
        Retorna (aluno, score). 'aluno' vem None se nao houver correspondencia
        acima do limiar, mesmo assim 'score' informa o quao perto chegou do
        candidato mais proximo (util para calibrar o threshold).
        """
        if self._cache_embeddings is None:
            self.carregar_cache()

        embedding = self.extrair_embedding(frame)
        if embedding is None or len(self._cache_embeddings) == 0:
            return None, 0.0

        # similaridade de cosseno contra todos os embeddings cadastrados de uma vez (numpy, rapido)
        norm_query = embedding / np.linalg.norm(embedding)
        norm_db = self._cache_embeddings / np.linalg.norm(self._cache_embeddings, axis=1, keepdims=True)
        similaridades = norm_db @ norm_query

        idx = int(np.argmax(similaridades))
        score = float(similaridades[idx])

        if score >= self.match_threshold:
            return self._cache_alunos[idx], score
        return None, score
