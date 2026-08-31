# camera.py
# Wrapper simples sobre a webcam (via OpenCV).
# Uso:
#   with Camera() as cam:
#       frame = cam.capturar_frame()

import cv2


class Camera:
    """Acesso a webcam local. Indice 0 = camera padrao do computador."""

    def __init__(self, indice: int = 0):
        self.indice = indice
        self._video = None

    def __enter__(self):
        self._video = cv2.VideoCapture(self.indice)
        if not self._video.isOpened():
            raise RuntimeError(
                "Nao foi possivel acessar a webcam. Verifique se ela esta conectada "
                "e se nenhum outro programa esta usando ela."
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._video is not None:
            self._video.release()

    def capturar_frame(self):
        if self._video is None:
            raise RuntimeError("Camera nao foi iniciada. Use 'with Camera() as cam:'.")
        ret, frame = self._video.read()
        if not ret:
            raise RuntimeError("Falha ao capturar frame da webcam.")
        return frame
