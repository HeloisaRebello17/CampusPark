# baixar_modelos.py
# Baixa os dois modelos .onnx do reconhecimento facial (YuNet e SFace) para a pasta informada.
# Usado pelo Dockerfile; tambem funciona fora do Docker: python docker/baixar_modelos.py resources/models

import os
import sys
import urllib.request

MODELOS = {
    "face_detection_yunet_2023mar.onnx":
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "face_recognition_sface_2021dec.onnx":
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
}

# Abaixo disso o download veio como "ponteiro" do Git LFS, nao o arquivo de verdade
TAMANHO_MINIMO = 100 * 1024


def main(pasta):
    os.makedirs(pasta, exist_ok=True)
    for nome, url in MODELOS.items():
        destino = os.path.join(pasta, nome)
        if os.path.exists(destino) and os.path.getsize(destino) >= TAMANHO_MINIMO:
            print(f"[OK] {nome} ja existe")
            continue
        print(f"Baixando {nome}...")
        urllib.request.urlretrieve(url, destino)
        tamanho = os.path.getsize(destino)
        if tamanho < TAMANHO_MINIMO:
            os.remove(destino)
            raise SystemExit(f"[FALHA] {nome} veio com {tamanho} bytes (ponteiro Git LFS?)")
        print(f"[OK] {nome} ({tamanho // 1024} KB)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join("resources", "models"))
