# CampusPark — Dependências entre Arquivos

> Este documento responde uma pergunta prática: **"para este arquivo funcionar, o que precisa
> existir antes dele?"** — pacotes instalados, variáveis de ambiente, outros arquivos do projeto,
> migrations aplicadas. Útil tanto para saber a **ordem de implementação** quanto para debugar um
> erro de "não achei X" na hora de rodar o projeto.
>
> Para o *código* de cada arquivo, ver `guia_desenvolvimento.md`. Para a razão de cada camada
> existir, ver `arquitetura.md` e `decisoes_tecnicas.md`.

---

## 1. Ordem de implementação recomendada

Os arquivos não são independentes — cada camada só funciona se a anterior já existir. Ordem sugerida:

```
1º  .env / .env.example              (nada funciona sem isso)
2º  requirements.txt → pip install   (bibliotecas do projeto)
3º  config/settings/base.py, dev.py  (Django não sobe sem settings válido)
4º  config/urls.py                    (mesmo vazio, precisa existir)
5º  apps/usuario  (models → migration → admin → serializers → services → views → urls)
6º  apps/veiculo  (depende do Aluno já existir)
7º  apps/acesso   (depende de Veiculo e Operador já existirem)
8º  core/middleware.py, permissions.py (dependem de já haver usuários/perfis para checar)
9º  integrations/ (rfid_reader, camera, facial_recognition — usados pelas views de acesso)
10º templates/ e static/ (telas que consomem os endpoints já prontos)
```

> Regra prática: **nunca comece um app que depende de FK de outro app que ainda não tem migration
> aplicada.** `apps/veiculo` importa `Aluno` de `apps/usuario` — se `usuario` não estiver migrado,
> a migration de `veiculo` falha.

---

## 2. Dependências por arquivo

### `.env`
- **Precisa de:** nada (é o ponto de partida).
- **É pré-requisito de:** todo o `config/settings/`, pois `python-decouple` lê as variáveis daqui.
- Sem ele: `SECRET_KEY` e `DATABASE_URL` ficam indefinidos e o Django não sobe.

### `requirements.txt` → ambiente virtual
- **Precisa de:** Python 3.12+ instalado e `.venv` ativo.
- **É pré-requisito de:** absolutamente tudo que importa `django`, `rest_framework`, `decouple`, etc.
- Sem ele: qualquer `import django` falha com `ModuleNotFoundError`.

### `config/settings/base.py`
- **Precisa de:** `.env` preenchido (lido via `decouple.config(...)`).
- **Precisa referenciar:** todos os apps em `INSTALLED_APPS` (`apps.usuario`, `apps.veiculo`,
  `apps.acesso`) — se um app ainda não existe fisicamente, o Django falha ao subir.
- **É pré-requisito de:** `config/settings/dev.py`/`prod.py` (que importam `from .base import *`),
  e de todo o projeto (é o `DJANGO_SETTINGS_MODULE`).

### `config/settings/dev.py` / `prod.py`
- **Precisa de:** `base.py` já definido.
- **É pré-requisito de:** qual settings o `manage.py` vai carregar (`DJANGO_SETTINGS_MODULE` no `.env`).

### `config/urls.py`
- **Precisa de:** as `urls.py` de cada app já existirem (`apps.usuario.urls`, `apps.veiculo.urls`,
  `apps.acesso.urls`) — o `include()` falha se o módulo não existir.
- **É pré-requisito de:** qualquer requisição HTTP chegar às views.

### `apps/usuario/models.py` (Aluno, Operador, TipoOperador)
- **Precisa de:** `apps.usuario` estar em `INSTALLED_APPS`.
- **Precisa rodar:** `python manage.py makemigrations usuario` + `migrate` antes de qualquer outro
  app poder referenciar `Aluno` via FK.
- **É pré-requisito de:** `apps/veiculo/models.py` (FK `aluno`), `apps/acesso/models.py`
  (indiretamente, via `Veiculo.aluno`), `core/middleware.py` (que verifica perfil de usuário logado).

### `apps/usuario/admin.py`
- **Precisa de:** `models.py` já migrado.
- **É pré-requisito de:** RF15 (administração via Django Admin) — sem isso, não existe tela de
  gestão de usuários pronta.

### `apps/usuario/serializers.py`
- **Precisa de:** `models.py`.
- **É pré-requisito de:** `views.py` do mesmo app (serializer é o contrato de entrada/saída da API).

### `apps/usuario/services.py`
- **Precisa de:** `models.py`.
- **É pré-requisito de:** `views.py` — a view chama o service, nunca acessa o model diretamente
  para regra de negócio (ver ADR-003 em `decisoes_tecnicas.md`).

### `apps/usuario/views.py` + `urls.py`
- **Precisa de:** `serializers.py`, `services.py`, e estar referenciado em `config/urls.py`.
- **É pré-requisito de:** o front-end (`templates/usuario/login.html`) conseguir autenticar.

---

### `apps/veiculo/models.py` (Veiculo)
- **Precisa de:** `Aluno` já migrado em `apps/usuario` (FK obrigatória — RN04).
- **Precisa rodar:** `makemigrations veiculo` + `migrate` **depois** da migration de `usuario`.
- **É pré-requisito de:** `apps/acesso/models.py` (FK `veiculo`).

### `apps/veiculo/validators.py`
- **Precisa de:** `models.py` (consulta `Veiculo.objects` para checar TAG duplicada — RN03).
- **É pré-requisito de:** `serializers.py`/`services.py` chamarem a validação antes de salvar.

### `apps/veiculo/views.py` + `urls.py`
- **Precisa de:** `serializers.py`, `validators.py`, registrado em `config/urls.py`.
- **É pré-requisito de:** telas de cadastro/edição de veículo do aluno.

---

### `apps/acesso/models.py` (RegistroAcesso)
- **Precisa de:** `Veiculo` (apps/veiculo) e `Operador` (apps/usuario) já migrados.
- **Precisa rodar:** `makemigrations acesso` + `migrate` **por último** entre os três apps de domínio.
- **É pré-requisito de:** `services.py` (não há o que consultar sem a tabela existir).

### `apps/acesso/services.py` (AcessoService)
- **Precisa de:** `models.py` (RegistroAcesso), e de `Veiculo`/`Aluno` já populados com dados de teste
  para validar manualmente (RN05–RN07).
- **É pré-requisito de:** `views.py` (EntradaView/SaidaView chamam o service).

### `apps/acesso/views.py` + `urls.py`
- **Precisa de:** `services.py`, `serializers.py`, registrado em `config/urls.py`.
- **É pré-requisito de:** o hardware (leitor RFID) ou a simulação conseguir chamar `/api/acesso/entrada/`
  e `/api/acesso/saida/`.

---

### `core/middleware.py` (PerfilAccessMiddleware)
- **Precisa de:** modelo de usuário com campo de perfil/`is_staff` já existente (`apps/usuario`).
- **Precisa estar listado em:** `MIDDLEWARE` dentro de `config/settings/base.py` — se não estiver
  na lista, o Django simplesmente não o executa (erro silencioso mais comum).
- **É pré-requisito de:** RNF14 funcionar (bloqueio de rota por perfil).

### `core/permissions.py`
- **Precisa de:** `apps/usuario/models.py` (para diferenciar Aluno/Operador/Admin).
- **É pré-requisito de:** qualquer `APIView`/`ViewSet` que declare `permission_classes = [...]`.

### `core/exceptions.py`
- **Precisa de:** nada de domínio — mas para funcionar como handler global precisa estar
  referenciado em `REST_FRAMEWORK = {"EXCEPTION_HANDLER": "core.exceptions.handler"}` em `base.py`.
- **É pré-requisito de:** RF16 (mensagens de erro padronizadas) em toda a API.

---

### `integrations/rfid_reader.py`
- **Precisa de:** nada do Django diretamente (é uma classe isolada) — mas para ser útil precisa
  ser chamado a partir de `apps/acesso/views.py`, passando a TAG lida para o `AcessoService`.
- **É pré-requisito de:** o fluxo de entrada funcionar fora do modo "digitar TAG manualmente via API".

### `integrations/camera.py` / `facial_recognition.py`
- **Precisa de:** `Pillow` instalado (`requirements.txt`).
- **É pré-requisito de:** apenas das fases futuras (fora do MVP) — hoje não bloqueiam nada.

---

### `templates/usuario/login.html`
- **Precisa de:** `apps/usuario/views.py` já expor uma view de login (server-rendered, não API).
- **Precisa de:** `templates/base.html` existir, se usar `{% extends "base.html" %}`.
- **Precisa de:** `TEMPLATES["DIRS"]` em `base.py` apontando para a pasta `templates/` (ver
  `guia_desenvolvimento.md`, settings).

### `static/css/usuario.css`, `static/js/usuario.js`
- **Precisa de:** `STATIC_URL` e `STATICFILES_DIRS` configurados em `base.py`.
- **Precisa de:** template referenciando via `{% load static %}` + `{% static "css/usuario.css" %}`.
- Em produção, precisa de `python manage.py collectstatic` antes do deploy.

---

## 3. Checklist de "por que não está funcionando"

Quando algo não sobe, verificar nesta ordem (segue a cadeia de dependência):

1. `.env` existe e está preenchido?
2. Ambiente virtual ativo e `pip install -r requirements.txt` rodado?
3. `DJANGO_SETTINGS_MODULE` no `.env` aponta para o settings certo (`config.settings.dev`)?
4. Todos os apps estão em `INSTALLED_APPS`?
5. Migrations aplicadas **na ordem certa** (`usuario` → `veiculo` → `acesso`)?
6. O app/model que está faltando tem `migrations/__init__.py`?
7. A `urls.py` do app está incluída em `config/urls.py`?
8. Se for erro de permissão/perfil: `core/middleware.py` está na lista `MIDDLEWARE`?
9. Se for erro de template/CSS: `TEMPLATES`/`STATICFILES_DIRS` apontam para as pastas certas?
