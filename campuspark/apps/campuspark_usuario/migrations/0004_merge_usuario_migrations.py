# Migration de merge: une as duas pontas divergentes de "0003_" criadas
# em paralelo por pessoas diferentes (nenhuma mexe na mesma coluna/dado).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('campuspark_usuario', '0003_alter_aluno_email_institucional'),
        ('campuspark_usuario', '0003_seed_tipo_operador'),
    ]

    operations = []
