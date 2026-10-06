# Dockerfile
# Imagem do sistema web do CampusPark (Django + reconhecimento facial no servidor).
# Use pelo docker-compose.yml da raiz do repositorio: docker compose up --build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# libglib2.0-0: exigida pelo OpenCV mesmo na versao headless
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Dependencias: o container nao tem tela, entao usa o OpenCV "headless" (sem janelas).
# mysqlclient fica de fora: o projeto usa PostgreSQL e ele exigiria compilador.
COPY requirements.txt .
RUN grep -iv '^mysqlclient' requirements.txt \
        | sed 's/^opencv-contrib-python/opencv-contrib-python-headless/' > /tmp/requirements.txt \
    && pip install -r /tmp/requirements.txt

# Modelos .onnx do reconhecimento facial: baixados aqui, uma vez, na construcao da imagem.
COPY docker/baixar_modelos.py docker/baixar_modelos.py
RUN python docker/baixar_modelos.py resources/models

COPY . .

# Remove CRLF caso o Git no Windows tenha convertido o script (senao o Linux nao o executa)
RUN sed -i 's/\r$//' docker/entrypoint.sh && chmod +x docker/entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
