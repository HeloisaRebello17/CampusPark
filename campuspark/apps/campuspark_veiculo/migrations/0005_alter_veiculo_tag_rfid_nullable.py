# Torna "tag_rfid" opcional no banco (NULL permitido), alinhando com o
# models.py: a tag e atribuida pela seguranca depois do autocadastro do
# aluno, entao nao existe no momento em que o veiculo e criado.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campuspark_veiculo', '0004_remove_veiculo_modelo_ano_and_tipo_veiculo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='veiculo',
            name='tag_rfid',
            field=models.CharField(blank=True, max_length=30, null=True, unique=True),
        ),
    ]
