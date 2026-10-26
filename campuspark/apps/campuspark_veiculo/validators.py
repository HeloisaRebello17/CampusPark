import re

from django.core.exceptions import ValidationError
from .models import Veiculo

# Placa no padrão antigo (ABC1234) ou Mercosul (ABC1D23), já sem hífen e em maiúsculas.
PLACA_REGEX = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")

def validar_tag_unica(tag_rfid, veiculo_id=None):
    qs = Veiculo.objects.filter(tag_rfid=tag_rfid)
    if veiculo_id:
        qs = qs.exclude(id=veiculo_id)
    if qs.exists():
        raise ValidationError("Esta TAG RFID já está associada a outro veículo.")