# Remove os campos "modelo_ano" e "tipo_veiculo" (substituidos por
# "fabricante"/"modelo"/"tipo", que ja existiam do lado do administrador).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('campuspark_veiculo', '0003_merge_veiculo_migrations'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='veiculo',
            name='modelo_ano',
        ),
        migrations.RemoveField(
            model_name='veiculo',
            name='tipo_veiculo',
        ),
    ]
