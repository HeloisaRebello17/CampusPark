from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campuspark_acesso', '0004_aberturacancela'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracaoestacionamento',
            name='exigir_face_saida',
            field=models.BooleanField(default=False),
        ),
    ]
