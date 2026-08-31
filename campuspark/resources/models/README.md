# Modelos de reconhecimento facial

Esta pasta precisa conter 2 arquivos `.onnx` que **não vêm no repositório**
(são arquivos binários, não fazem sentido versionar como código-fonte).
Baixe os dois e coloque exatamente aqui dentro de `resources/models/`:

- `face_detection_yunet_2023mar.onnx` — detecta o rosto no frame
- `face_recognition_sface_2021dec.onnx` — gera o vetor (embedding) do rosto

## Como baixar (Windows / PowerShell)

Abra o PowerShell **dentro desta pasta** (`resources/models`) e rode:

```powershell
Invoke-WebRequest -Uri "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx" -OutFile "face_detection_yunet_2023mar.onnx"

Invoke-WebRequest -Uri "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx" -OutFile "face_recognition_sface_2021dec.onnx"
```

Se preferir, também pode simplesmente colar os dois links acima no navegador —
o download começa automaticamente.

## Como confirmar que deu certo

Depois de baixar, esta pasta deve ter:

```
resources/models/
├── README.md
├── face_detection_yunet_2023mar.onnx      (~230 KB)
└── face_recognition_sface_2021dec.onnx    (~37 MB)
```

Se o tamanho do arquivo baixado ficar em poucos KB (tipo 100-150 bytes) e
abrindo ele em um editor de texto aparecer algo como `version
https://git-lfs.github.com/...`, o download não pegou o arquivo real —
tente de novo, ou baixe pelo navegador em vez do PowerShell.
