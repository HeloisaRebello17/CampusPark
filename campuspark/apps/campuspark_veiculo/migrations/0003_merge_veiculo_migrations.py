# Migration de merge: une as duas pontas divergentes de "0002_" criadas
# em paralelo por pessoas diferentes (nenhuma mexe na mesma coluna).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('campuspark_veiculo', '0002_veiculo_autorizado_veiculo_cor_veiculo_data_criacao_and_more'),
        ('campuspark_veiculo', '0002_veiculo_modelo_ano_veiculo_seguro_ativo_and_more'),
    ]

    operations = []
