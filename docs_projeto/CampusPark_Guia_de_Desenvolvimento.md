# CampusPark — Guia de Desenvolvimento

**Projeto:** Sistema de Controle de Acesso ao Estacionamento — Centro Universitário Católica de Santa Catarina
**Stack de implementação:** Python 3.12+ / Django 5.x / Django REST Framework

> A estrutura de pastas, modelo de dados e convenções de código estão em `arquitetura.md`.
> Este documento cobre como configurar o ambiente, rodar o projeto e o código base de cada módulo.

---

## 1. Configuração de Ambiente

**.env.example** (versionar este, nunca o `.env` real):
```
DJANGO_SECRET_KEY=troque-esta-chave
DJANGO_DEBUG=True
DJANGO_SETTINGS_MODULE=config.settings.dev
DATABASE_URL=mysql://user:senha@localhost:3306/campuspark
ALLOWED_HOSTS=localhost,127.0.0.1
```

**requirements.txt** (base sugerida para o MVP):
```
Django>=5.0,<6.0
djangorestframework>=3.15
python-decouple>=3.8
mysqlclient>=2.2      # ou psycopg2-binary se optarem por PostgreSQL
django-cors-headers>=4.3
Pillow>=10.0           # necessário para foto/reconhecimento facial futuro
```

**config/settings/base.py** (trecho essencial):
```python
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("DJANGO_SECRET_KEY")
DEBUG = config("DJANGO_DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.usuario",
    "apps.veiculo",
    "apps.acesso",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "core.middleware.PerfilAccessMiddleware",   # RNF14
]

ROOT_URLCONF = "config.urls"
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
```

---

## 2. Código Base por Módulo

### `apps/usuario/models.py`
```python
from django.db import models

class Aluno(models.Model):
    matricula = models.CharField(max_length=7, unique=True)
    cpf = models.CharField(max_length=11, unique=True)
    nome_completo = models.CharField(max_length=200)
    email_institucional = models.EmailField(max_length=64)
    senha_hash = models.CharField(max_length=255)
    ativo = models.BooleanField(default=True)      # necessário para RF07/RF11
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.matricula} - {self.nome_completo}"


class TipoOperador(models.Model):
    descricao = models.CharField(max_length=30)


class Operador(models.Model):
    tipo_operador = models.ForeignKey(TipoOperador, on_delete=models.PROTECT)
    cpf = models.CharField(max_length=11, unique=True)
    nome_completo = models.CharField(max_length=200)
    email = models.EmailField(max_length=255)
    data_criacao = models.DateTimeField(auto_now_add=True)
```

### `apps/veiculo/models.py`
```python
from django.db import models
from apps.usuario.models import Aluno

class Veiculo(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name="veiculos")
    placa = models.CharField(max_length=7, unique=True)
    renavam = models.CharField(max_length=11, unique=True, blank=True, null=True)
    tipo = models.CharField(max_length=20)  # carro, moto...
    fabricante = models.CharField(max_length=30, blank=True)
    modelo = models.CharField(max_length=30, blank=True)
    cor = models.CharField(max_length=20, blank=True)
    tag_rfid = models.CharField(max_length=30, unique=True)
    autorizado = models.BooleanField(default=True)   # RF07, RF11
    data_criacao = models.DateTimeField(auto_now_add=True)
```

### `apps/veiculo/validators.py`
```python
from django.core.exceptions import ValidationError
from .models import Veiculo

def validar_tag_unica(tag_rfid, veiculo_id=None):
    qs = Veiculo.objects.filter(tag_rfid=tag_rfid)
    if veiculo_id:
        qs = qs.exclude(id=veiculo_id)
    if qs.exists():
        raise ValidationError("Esta TAG RFID já está associada a outro veículo.")  # RN03
```

### `apps/acesso/models.py`
```python
from django.db import models
from apps.veiculo.models import Veiculo
from apps.usuario.models import Operador

class StatusAcesso(models.TextChoices):
    DENTRO = "DENTRO", "Dentro do estacionamento"
    FINALIZADO = "FINALIZADO", "Saída registrada"
    NEGADO = "NEGADO", "Acesso negado"

class RegistroAcesso(models.Model):
    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name="registros")
    operador = models.ForeignKey(Operador, on_delete=models.SET_NULL, null=True, blank=True)
    data_entrada = models.DateTimeField(auto_now_add=True)
    data_saida = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=StatusAcesso.choices, default=StatusAcesso.DENTRO)
```

### `apps/acesso/services.py` — o coração das regras de negócio (RF06, RF07, RF11, RN05–RN07)
```python
from django.utils import timezone
from apps.veiculo.models import Veiculo
from .models import RegistroAcesso, StatusAcesso

class AcessoNegado(Exception):
    pass

class AcessoService:

    @staticmethod
    def validar_entrada(tag_rfid: str, operador=None) -> RegistroAcesso:
        try:
            veiculo = Veiculo.objects.select_related("aluno").get(tag_rfid=tag_rfid)
        except Veiculo.DoesNotExist:
            raise AcessoNegado("TAG não encontrada no sistema.")  # RF11

        if not veiculo.autorizado or not veiculo.aluno.ativo:
            raise AcessoNegado("Veículo ou aluno não autorizado.")  # RF07 / RF11

        ja_dentro = RegistroAcesso.objects.filter(
            veiculo=veiculo, status=StatusAcesso.DENTRO
        ).exists()
        if ja_dentro:
            raise AcessoNegado("Este veículo já possui uma entrada em aberto.")  # RN05

        return RegistroAcesso.objects.create(veiculo=veiculo, operador=operador)

    @staticmethod
    def registrar_saida(tag_rfid: str) -> RegistroAcesso:
        registro = RegistroAcesso.objects.filter(
            veiculo__tag_rfid=tag_rfid, status=StatusAcesso.DENTRO
        ).order_by("-data_entrada").first()

        if not registro:
            raise AcessoNegado("Não há entrada em aberto para esta TAG.")  # RN06

        registro.data_saida = timezone.now()
        registro.status = StatusAcesso.FINALIZADO
        registro.save(update_fields=["data_saida", "status"])
        return registro
```

### `apps/acesso/views.py`
```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import AcessoService, AcessoNegado
from .serializers import RegistroAcessoSerializer

class EntradaView(APIView):
    def post(self, request):
        tag = request.data.get("tag_rfid")
        try:
            registro = AcessoService.validar_entrada(tag)
        except AcessoNegado as e:
            return Response({"erro": str(e)}, status=status.HTTP_403_FORBIDDEN)
        return Response(RegistroAcessoSerializer(registro).data, status=201)


class SaidaView(APIView):
    def post(self, request):
        tag = request.data.get("tag_rfid")
        try:
            registro = AcessoService.registrar_saida(tag)
        except AcessoNegado as e:
            return Response({"erro": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RegistroAcessoSerializer(registro).data, status=200)
```

### `apps/acesso/urls.py`
```python
from django.urls import path
from .views import EntradaView, SaidaView

urlpatterns = [
    path("entrada/", EntradaView.as_view(), name="acesso-entrada"),
    path("saida/", SaidaView.as_view(), name="acesso-saida"),
]
```

### `config/urls.py`
```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/usuario/", include("apps.usuario.urls")),
    path("api/veiculo/", include("apps.veiculo.urls")),
    path("api/acesso/", include("apps.acesso.urls")),
]
```

### `integrations/rfid_reader.py` (simulado no MVP)
```python
class RFIDReader:
    """No MVP a leitura é simulada — troca-se por SDK real do leitor físico depois."""

    def ler_tag(self) -> str:
        # TODO: integrar com hardware real (RF06)
        return input("Simulação: digite a TAG lida pelo leitor -> ").strip()
```

### `core/middleware.py` — controle de acesso por perfil (RNF14)
```python
from django.http import JsonResponse

class PerfilAccessMiddleware:
    ROTAS_ADMIN = ["/api/usuario/gerenciar/"]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if any(request.path.startswith(r) for r in self.ROTAS_ADMIN):
            if not request.user.is_authenticated or not request.user.is_staff:
                return JsonResponse({"erro": "Acesso restrito a administradores."}, status=403)
        return self.get_response(request)
```

---

## 3. Guia de Setup para Novos Desenvolvedores

1. **Clonar o repositório** e criar branch a partir de `develop`.
2. **Criar ambiente virtual:** `python -m venv .venv` e ativar.
3. **Instalar dependências:** `pip install -r requirements.txt`.
4. **Copiar `.env.example` para `.env`** e preencher as variáveis locais.
5. **Rodar migrations:** `python manage.py migrate`.
6. **Criar superusuário (admin):** `python manage.py createsuperuser`.
7. **Rodar o servidor:** `python manage.py runserver`.
8. **Rodar os testes antes de abrir PR:** `python manage.py test`.
9. Abrir PR para `develop` com descrição do RF/RN atendido.

---

## 4. Checklist de Qualidade (usar em todo PR)

- [ ] Regra de negócio está no `services.py`, não na view?
- [ ] Existe teste cobrindo o caminho feliz e pelo menos um caminho de erro (RN violada)?
- [ ] Mensagens de erro seguem RF16 (claras, indicam a inconsistência)?
- [ ] Dados sensíveis (CPF, matrícula) não aparecem em logs (RNF11)?
- [ ] Migration gerada e commitada junto com a mudança de model?
- [ ] Endpoint novo documentado (mínimo: método, path, payload, respostas) em `docs_projeto/`?

---

## 5. Divisão da Equipe (referência do MVP)

| Integrante | Responsabilidade |
|---|---|
| Gabrieli Eduarda Lembeck | Backend/API e integração |
| Heloisa Rebello Cabral | Banco de dados e persistência |
| Julio Bezerra de Mattos Manoel | Frontend — telas do aluno e veículo |
| **Mileine da Silva de Freitas** | **Segurança — RFID, entrada e saída** (`apps/acesso`, `integrations/rfid_reader.py`) |
| Thomas Henry Steinback | Administrador — CRUD e testes |
| Ana Julia Castelo Branco | Integração, testes e documentação |

Dado o seu módulo (Segurança/Acesso), o foco de código deve estar em `apps/acesso/`,
`integrations/rfid_reader.py` e nas regras RN05, RN06 e RN07 mostradas no `AcessoService` acima.

---

## 6. Próximos Passos Fora do MVP (não implementar agora)

Reconhecimento facial real, integração física com leitor RFID, dashboard avançado, relatórios,
notificações, app mobile, controle de vagas em tempo real e integrações externas — mantidos fora
do escopo da primeira quinzena conforme o documento do MVP.
