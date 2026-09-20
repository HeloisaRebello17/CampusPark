from django.db import migrations


def criar_tipos_operador(apps, schema_editor):
    TipoOperador = apps.get_model("campuspark_usuario", "TipoOperador")
    for descricao in ("Portaria", "Administrador"):
        TipoOperador.objects.get_or_create(descricao=descricao)


def remover_tipos_operador(apps, schema_editor):
    TipoOperador = apps.get_model("campuspark_usuario", "TipoOperador")
    TipoOperador.objects.filter(descricao__in=("Portaria", "Administrador")).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("campuspark_usuario", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(criar_tipos_operador, remover_tipos_operador),
    ]
