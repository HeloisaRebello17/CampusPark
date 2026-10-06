# CampusPark — Como rodar a aplicação

Guia para quem vai baixar e rodar o projeto pela primeira vez. Com o Docker, não é preciso instalar
Python, criar venv nem baixar os modelos de reconhecimento facial: tudo isso é feito automaticamente.

---

## 1. O que instalar (uma vez só)

| Programa | Para quê | Onde baixar |
|---|---|---|
| **Git** | Baixar o código do repositório | https://git-scm.com/downloads |
| **Docker Desktop** | Rodar o sistema (servidor + banco) | https://www.docker.com/products/docker-desktop/ |

No **Windows**, o Docker Desktop usa o **WSL 2**. Se o instalador pedir para ativá-lo ou para
reiniciar o computador, aceite. Se ele não ativar sozinho, abra o PowerShell **como administrador**,
rode o comando abaixo e reinicie o computador:

```powershell
wsl --install
```

**Como confirmar:** abra o Docker Desktop, espere aparecer **"Engine running"** no canto inferior
esquerdo e rode no PowerShell (ou no terminal, no Mac/Linux):

```powershell
git --version
docker --version
docker compose version
```

Os três comandos devem mostrar um número de versão.

---

## 2. Baixar o projeto

```powershell
git clone https://github.com/HeloisaRebello17/CampusPark.git
cd CampusPark
```

> Se a URL do repositório for outra, use a que aparece no botão verde **"Code"** do GitHub.
> Para usar uma branch específica: `git checkout <nome-da-branch>`.

---

## 3. Escolher o banco de dados

Existem duas opções. Escolha uma:

### Opção A — Banco local (mais simples, para testar)

Não faça nada: sem o arquivo `.env`, o Docker sobe um PostgreSQL próprio no seu computador.
Ele **começa vazio** e os dados ficam só na sua máquina.

### Opção B — Banco compartilhado do time

Peça a string de conexão (`DATABASE_URL`) para quem administra o banco (hoje: **Heloisa**) e crie
o arquivo `campuspark/.env` a partir do modelo:

```powershell
copy campuspark\.env.example campuspark\.env
notepad campuspark\.env
```

> No Mac/Linux use `cp campuspark/.env.example campuspark/.env` e abra o arquivo em qualquer editor.

Preencha o arquivo assim:

```
DJANGO_SECRET_KEY=<qualquer texto longo e aleatório>
DJANGO_DEBUG=True
DJANGO_SETTINGS_MODULE=config.settings
DATABASE_URL=postgresql://usuario:senha@host:5432/nome_do_banco?sslmode=require
ALLOWED_HOSTS=localhost,127.0.0.1
```

> O `.env` contém a senha do banco: **nunca** faça commit dele nem o envie para terceiros.
> Ele já está no `.gitignore`.

---

## 4. Subir a aplicação

Com o Docker Desktop aberto, rode na pasta raiz do projeto (onde está o `docker-compose.yml`):

```powershell
docker compose up --build
```

Na primeira vez esse comando demora alguns minutos, porque baixa as dependências e os modelos de
reconhecimento facial. Nas próximas vezes é bem mais rápido.

**Como confirmar:** no final do log aparece algo como:

```
web-1  | Aplicando migrations...
web-1  | System check identified no issues (0 silenced).
```

Então abra no navegador: **http://localhost:8000**

Para parar, use `Ctrl + C` no terminal. Para subir em segundo plano, liberando o terminal, use
`docker compose up -d`; nesse caso, pare com `docker compose down`.

---

## 5. Primeiro acesso

| Endereço | O que é |
|---|---|
| http://localhost:8000/cadastro/ | Cadastro de aluno (com captura do rosto pela câmera do navegador) |
| http://localhost:8000/login/ | Login do aluno |
| http://localhost:8000/admin/ | Painel administrativo do Django (operadores, tipos de operador, etc.) |

Para entrar no `/admin/`, crie um superusuário com o comando abaixo. Ele pede usuário, e-mail e
senha:

```powershell
docker compose exec web python manage.py createsuperuser
```

> No **banco local** (opção A) não existe nenhum usuário. Cadastre um aluno pela tela de cadastro e
> crie o superusuário para acessar o `/admin/`.

---

## 6. Comandos do dia a dia

Rode todos na pasta raiz do projeto.

| Comando | Para quê |
|---|---|
| `docker compose up --build` | Subir (e atualizar depois de mudar o código ou dar `git pull`) |
| `docker compose up -d` | Subir em segundo plano |
| `docker compose down` | Parar tudo |
| `docker compose logs -f web` | Ver os logs do servidor |
| `docker compose exec web python manage.py createsuperuser` | Criar usuário do `/admin/` |
| `docker compose exec web python manage.py simular_acesso <TAG> --matricula <MATRICULA>` | Simular a entrada de um veículo |
| `docker compose exec web python manage.py simular_acesso <TAG> --saida` | Simular a saída |
| `docker compose down -v` | Parar e **apagar o banco local** (opção A) para começar do zero |

> O código fica **dentro da imagem**. Depois de editar qualquer arquivo, rode
> `docker compose up --build` de novo para ver a mudança.

---

## 7. Reconhecimento facial pela webcam (fora do Docker)

O programa de reconhecimento em tempo real (`campuspark/reconhecimento_app.py`) abre a webcam e
uma janela na tela. Um container **não consegue fazer isso** no Windows/Mac, por isso ele roda
separado, como `.exe`. O cadastro facial pela tela de cadastro (navegador) funciona normalmente
no Docker.

Para gerar o `.exe` no Windows:

1. Instale o **Python 3.12** (https://www.python.org/downloads/) e, no instalador, marque
   **"Add python.exe to PATH"**.
2. Crie o `campuspark/.env` com a `DATABASE_URL` (veja a opção B do passo 3). O `.exe` precisa
   acessar o mesmo banco que o sistema web.
3. Baixe os modelos de reconhecimento facial:
   ```powershell
   cd campuspark
   python docker\baixar_modelos.py resources\models
   ```
4. Dê dois cliques em `campuspark\build_exe.bat`. O programa gerado fica em
   `campuspark\dist\CampusPark_Reconhecimento\CampusPark_Reconhecimento.exe`.

Para confirmar que ele acessa o banco, os modelos e a webcam:
`CampusPark_Reconhecimento.exe --teste`

---

## 8. Problemas comuns

| Sintoma | Solução |
|---|---|
| `failed to connect to the docker API` / `daemon is not running` | Abra o Docker Desktop e espere o "Engine running". |
| Docker Desktop fecha com erro `initializing Inference manager ... dockerInference` | Feche o Docker, abra `%APPDATA%\Docker\settings-store.json`, deixe `"EnableDockerAI": false` e adicione `"EnableInference": false,`. Depois abra o Docker de novo. |
| `port is already allocated` (porta 8000 ocupada) | Feche o outro programa que usa a porta (ex.: um `runserver` aberto fora do Docker) ou troque `"8000:8000"` por `"8080:8000"` no `docker-compose.yml` e acesse http://localhost:8080. |
| Erro de conexão com o banco usando a opção B | Confira a `DATABASE_URL` no `campuspark/.env`: sem espaços antes ou depois do `=` e com `?sslmode=require` no final, se o banco exigir. |
| Mudei o código e nada mudou no navegador | Rode `docker compose up --build`. |
| Quero apagar tudo e começar do zero | `docker compose down -v` e depois `docker compose up --build`. |
| Câmera não abre na tela de cadastro | Acesse por `http://localhost:8000`, não pelo IP da máquina: o navegador só libera a câmera em `localhost` ou `https`. |
