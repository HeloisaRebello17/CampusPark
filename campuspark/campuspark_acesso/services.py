# services.py
# Serviços de validação de acesso usando RFID e reconhecimento facial.
from integrations.rfid_reader import ler_tag
from integrations.facial_recognition import validar_rosto

def validar_entrada(tag):
    # Valida entrada apenas com RFID
    return ler_tag(tag)

def validar_saida(tag, imagem):
    # Valida saída com RFID + facial
    return ler_tag(tag) and validar_rosto(imagem)
