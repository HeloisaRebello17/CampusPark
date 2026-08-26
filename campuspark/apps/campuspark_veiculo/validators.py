from django.core.exceptions import ValidationError
from .models import Veiculo

def validar_tag_unica(tag_rfid, veiculo_id=None):
    qs = Veiculo.objects.filter(tag_rfid=tag_rfid)
    if veiculo_id:
        qs = qs.exclude(id=veiculo_id)
    if qs.exists():
        raise ValidationError("Esta TAG RFID já está associada a outro veículo.")