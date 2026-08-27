# CampusPark — Arquitetura

**Projeto:** Sistema de Controle de Acesso ao Estacionamento — Centro Universitário Católica de Santa Catarina
**Stack de implementação:** Python 3.12+ / Django 5.x / Django REST Framework
**Documento vivo** — atualizar sempre que a arquitetura mudar.

> Este documento cobre **estrutura de pastas, modelo de dados resumido e convenções de código**.
> Para os demais assuntos, ver os documentos irmãos em `docs_projeto/`:
> - `requisitos.md` — RF/RNF completos, regras de negócio (RN01–RN07), escopo do MVP
> - `modelo_dados.md` — detalhamento campo a campo de cada entidade, índices, diagrama lógico
> - `decisoes_tecnicas.md` — ADRs com o porquê de cada decisão estrutural
> - `guia_desenvolvimento.md` — setup, código base, checklist de PR

---

## 1. Visão Geral do Projeto

O CampusPark controla o acesso de veículos ao estacionamento do campus através de identificação
por **TAG RFID** (com QR Code e reconhecimento facial como camadas futuras), validando o vínculo
aluno → veículo → autorização e registrando entrada/saída em tempo real.

Módulos de negócio:

| Domínio | Responsabilidade | Requisitos relacionados |
|---|---|---|
| **Usuário/Aluno** | Cadastro, login, dados institucionais, perfil | RF01, RF13 — ver `requisitos.md` |
| **Veículo** | Cadastro de veículo, placa, TAG RFID, vínculo com aluno | RF02–RF05 — ver `requisitos.md` |
| **Acesso** | Leitura da TAG/QR, validação, registro de entrada/saída, histórico | RF06–RF11 — ver `requisitos.md` |
| **Operador/Admin** | Gestão de usuários, veículos, permissões | RF15 — ver `requisitos.md` |
| **Integrations** | Hardware: leitor RFID, câmera, reconhecimento facial (simulado no MVP) | RNF09, ADR-004 — ver `decisoes_tecnicas.md` |

Para a lista completa de requisitos funcionais/não funcionais e das regras de negócio (RN01–RN07)
que fundamentam a validação de entrada/saída, ver **`requisitos.md`**.

---

## 2. Modelo de Dados (resumo)

Entidades principais e seus relacionamentos:

```
Aluno 1 ──< Veiculo 1 ──< RegistroAcesso >── 1 Operador >── 1 TipoOperador
```

| Entidade | Campos-chave | Observação |
|---|---|---|
| `Aluno` | matricula (UNIQUE), cpf (UNIQUE), ativo | RN01 |
| `Veiculo` | placa (UNIQUE), tag_rfid (UNIQUE), aluno_id (FK), autorizado | RN02, RN03, RN04 |
| `Operador` / `TipoOperador` | cpf (UNIQUE), tipo_operador_id (FK) | Quem valida entrada/saída manualmente |
| `RegistroAcesso` | veiculo_id (FK), data_entrada, data_saida (nullable), status | RN05, RN06, RN07 |

> **Decisão de arquitetura:** unificamos `historico_entrada`/`historico_saida` (do diagrama ER
> original) em uma única tabela `RegistroAcesso` com `data_saida` anulável. O detalhamento campo a
> campo de cada entidade, os índices recomendados e a justificativa completa dessa unificação estão
> em **`modelo_dados.md`**; o racional da decisão em si (alternativas consideradas, consequências)
> está registrado como **ADR-002** em `decisoes_tecnicas.md`.

---

## 3. Arquitetura de Pastas (ajustada)

A estrutura que a equipe já tinha estava no caminho certo (separação por domínio), mas misturava
convenções do Flask/.NET (`routes.py`, `controllers.py`, `wwwroot/`) com Django. Padronizando 100%
em Django:

```
campuspark/                        # raiz do repositório
├── manage.py
├── requirements.txt
├── .env                           # NUNCA versionar (git-ignored)
├── .env.example                   # versionado, sem valores reais
├── .gitignore
├── README.md
│
├── docs_projeto/                  # documentação viva do projeto
│   ├── arquitetura.md             # este documento
│   ├── guia_desenvolvimento.md
│   ├── modelo_dados.md
│   ├── requisitos.md
│   └── decisoes_tecnicas.md
│
├── config/                        # settings do projeto Django (substitui a pasta "campuspark/")
│   ├── __init__.py
│   ├── asgi.py
│   ├── wsgi.py
│   ├── urls.py                    # inclui as urls de cada app
│   └── settings                   # configs comuns
│
├── core/                          # código transversal, sem regra de negócio de domínio
│   ├── __init__.py
│   ├── middleware.py              # ex.: controle de acesso por perfil (RNF14)
│   ├── permissions.py             # classes de permissão DRF (Admin/Operador/Aluno)
│   ├── exceptions.py              # exceptions customizadas + handler global
│   └── utils.py                   # helpers genéricos (antigo helpers.py)
│
├── integrations/                  # camada de hardware / serviços externos — ver ADR-004
│   ├── __init__.py
│   ├── rfid_reader.py             # leitura da TAG (simulada no MVP)
│   ├── camera.py                  # captura de imagem
│   └── facial_recognition.py      # validação facial (simulada no MVP)
│
├── apps/                          # todos os apps Django de domínio, agrupados — ver ADR-005
│   ├── usuario/                   # ex campuspark_usuario
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── admin.py
│   │   ├── models.py              # Aluno, Operador, TipoOperador — detalhe em modelo_dados.md
│   │   ├── serializers.py
│   │   ├── views.py                # substitui controllers.py
│   │   ├── urls.py                 # substitui routes.py
│   │   ├── services.py             # regras de negócio (cadastro, autenticação) — ver ADR-003
│   │   ├── tests.py
│   │   └── migrations/
│   │       └── __init__.py
│   │
│   ├── veiculo/                   # ex campuspark_veiculo
│   │   ├── __init__.py / apps.py / admin.py
│   │   ├── models.py               # Veiculo — detalhe em modelo_dados.md
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── validators.py           # validação de placa, RENAVAM, TAG única (RN02, RN03)
│   │   ├── tests.py
│   │   └── migrations/
│   │
│   └── acesso/                    # ex campuspark_acesso
│       ├── __init__.py / apps.py / admin.py
│       ├── models.py               # RegistroAcesso — detalhe em modelo_dados.md
│       ├── serializers.py
│       ├── views.py                 # endpoint chamado pela portaria/leitor
│       ├── urls.py
│       ├── services.py              # AcessoService: valida RF06, RF07, RN05, RN06, RN07
│       ├── tests.py
│       └── migrations/
│
├── templates/                     # substitui "view/" (padrão Django)
│   ├── base.html
│   ├── usuario/
│   │   └── login.html
│   └── acesso/
│
├── static/                        # substitui "wwwroot/" (padrão Django)
│   ├── css/
│   │   └── usuario.css
│   ├── js/
│   │   └── usuario.js
│   └── images/
│
└── tests/                         # testes de integração ponta a ponta (opcional)
    └── test_fluxo_acesso.py
```

Código completo de cada arquivo destacado acima (models, services, views, urls, middleware,
settings) está em **`guia_desenvolvimento.md`**.

### Por que essas mudanças?

| Antes | Depois | Motivo |
|---|---|---|
| `controllers.py` | `views.py` | Convenção Django; qualquer dev novo já sabe onde procurar |
| `routes.py` | `urls.py` | Idem — `urls.py` é o nome esperado pelo `include()` do Django |
| `wwwroot/` | `static/` | `wwwroot` é convenção ASP.NET; Django usa `STATIC_URL`/`static/` |
| `view/usuario/login.html` | `templates/usuario/login.html` | Django resolve templates por `templates/<app>/` |
| apps soltos na raiz | pasta `apps/` | Evita poluir a raiz do projeto conforme o número de apps cresce — ADR-005 |
| `settings.py` único | `settings/base.py, dev.py, prod.py` | Permite configs diferentes por ambiente sem `if DEBUG` espalhado |
| — | `permissions.py`, `exceptions.py` em `core/` | RNF14 (perfis) e RNF16 (mensagens de erro consistentes) exigem isso centralizado |
| stack C#/.NET planejada no relatório do PAC | Django/Python implementado | ADR-001 — motivo e consequências completos em `decisoes_tecnicas.md` |

---

## 4. Convenções de Código

- **Nomenclatura de apps:** singular, minúsculo, sem prefixo `campuspark_` (o prefixo já está implícito
  no nome do projeto/repositório) → `usuario`, `veiculo`, `acesso`.
- **Models:** `PascalCase`, singular (`Aluno`, não `Alunos`).
- **Campos de banco:** `snake_case` (`data_criacao`, `tag_rfid`).
- **Views:** preferir **DRF `ViewSet`/`APIView`** para endpoints consumidos pelo hardware/portaria e
  **Class-Based Views** (`TemplateView`, `FormView`) para telas server-rendered do aluno/admin.
- **Regra de negócio nunca na view.** A view só recebe request, chama o `service` e devolve resposta
  — motivo completo dessa escolha em **ADR-003** (`decisoes_tecnicas.md`).
- **Um `serializers.py` por app**, mesmo que simples — mantém contrato de API explícito.
- **Migrations:** nunca editar uma migration já commitada e mesclada; gerar uma nova.
- **Commits:** `tipo(escopo): descrição curta` — ex.: `feat(acesso): valida RN05 impedindo dupla entrada`.
- **Branches:** `feature/<nome>`, `fix/<nome>`, `docs/<nome>`, sempre a partir de `develop`.

---

## 5. Mapa de Referência Rápida

| Preciso saber... | Vou em... |
|---|---|
| Qual regra de negócio o sistema deve seguir | `requisitos.md` |
| Como um campo específico é tipado/restringido no banco | `modelo_dados.md` |
| Por que uma decisão estrutural foi tomada (e as alternativas descartadas) | `decisoes_tecnicas.md` |
| Como subir o ambiente e o código-fonte de cada módulo | `guia_desenvolvimento.md` |
| Onde um novo arquivo/app deve ficar | Este documento, seção 3 |
