# CampusPark — Guia de Instalação do Ambiente (do zero)

> Este guia assume que você **nunca configurou esse projeto antes** e não sabe nada de Python,
> Git ou Django. Siga os passos na ordem, sem pular nenhum. Cada seção tem uma parte de
> "Como confirmar que deu certo" — não avance sem confirmar.
>
> Testado em **Windows + PowerShell**. Se você usa Mac/Linux, os comandos de ativar o ambiente
> mudam um pouco — está marcado onde isso acontece.

---

## 0. O que você vai precisar antes de começar

- Ter o **Git** instalado ([git-scm.com](https://git-scm.com/downloads))
- Ter o **Python** instalado — versão **3.11** ou **3.12** (evite 3.13+; libs de visão
  computacional como o OpenCV às vezes demoram a lançar versões compatíveis com Python muito novo)
- Pedir para quem administra o banco (hoje: **Heloisa**) a string de conexão do banco
  (`DATABASE_URL`) — sem isso você não passa do passo 4
- Acesso ao repositório no GitHub (alguém do time precisa te adicionar como colaborador, ou o
  repositório precisa estar público)

### Verificando se já tem Git e Python instalados

Abra o **PowerShell** (procure "PowerShell" no menu Iniciar) e rode:

```powershell
git --version
python --version
```

- Se aparecer um número de versão em ambos (ex.: `git version 2.44.0` e `Python 3.11.9`), pode
  pular pra seção 1.
- Se der erro em algum dos dois (`não é reconhecido como um comando`), baixe e instale o que
  faltar:
  - Git: https://git-scm.com/downloads (aceite as opções padrão do instalador)
  - Python: https://www.python.org/downloads/ — **IMPORTANTE:** na primeira tela do instalador,
    marque a caixinha **"Add python.exe to PATH"** antes de clicar em instalar. Se esquecer isso,
    o comando `python` não vai funcionar depois.

Depois de instalar, **feche e abra o PowerShell de novo** e repita os dois comandos acima pra
confirmar.

---

## 1. Clonar o projeto

Escolha uma pasta no seu computador onde vai guardar o projeto (ex.: `D:\Faculdade\`) e, dentro
dela, no PowerShell:

```powershell
git clone https://github.com/<organizacao-ou-usuario>/CampusPark.git
cd CampusPark\campuspark
```

> Troque a URL acima pela URL real do repositório (o link que aparece no botão verde **"Code"**
> no GitHub). A partir daqui, **todo comando deste guia deve ser rodado dentro da pasta
> `CampusPark\campuspark`** (onde fica o arquivo `manage.py`) — confirme com:
> ```powershell
> dir manage.py
> ```
> Se aparecer o arquivo listado, você está no lugar certo.

Se seu time trabalha em branches separadas, troque para a branch certa antes de seguir:

```powershell
git checkout Thomas_dev
```

(troque `Thomas_dev` pelo nome da branch que você for usar)

---

## 2. Criar e ativar o ambiente virtual (venv)

O ambiente virtual isola as bibliotecas Python desse projeto do resto do seu computador.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Como confirmar que deu certo:** o início da linha do PowerShell deve mudar para mostrar
`(venv)` antes do caminho, tipo:
```
(venv) PS D:\Faculdade\CampusPark\campuspark>
```

### Se der erro "a execução de scripts foi desabilitada neste sistema"

O Windows bloqueia scripts `.ps1` por padrão. Rode isso uma vez (só libera para a janela atual,
não mexe na configuração do Windows todo) e tente ativar de novo:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

### Se der erro "não foi possível carregar o módulo 'venv'" ou "termo não reconhecido"

Provavelmente você esqueceu o `.\` na frente do comando, ou está de fora da pasta certa. Confirme
com `dir` que existe uma pasta `venv` ali, e use exatamente `.\venv\Scripts\Activate.ps1`
(com a extensão `.ps1` — sem ela o PowerShell não sabe o que fazer com o arquivo).

> **Mac/Linux:** o comando de ativar é `source venv/bin/activate` em vez do `.ps1` acima.

**Do próximo passo em diante, sempre confirme que o `(venv)` aparece no início da linha antes de
rodar qualquer comando `python` ou `pip`.** Se você fechar o PowerShell e abrir de novo depois,
precisa rodar o `.\venv\Scripts\Activate.ps1` de novo (a ativação não é permanente).

---

## 3. Instalar as dependências do projeto

Com o `(venv)` ativo:

```powershell
pip install -r requirements.txt
```

Isso demora um pouco — o OpenCV (biblioteca de visão computacional) é grande. Acompanhe o
progresso na tela; se travar por mais de 5-10 minutos sem nenhuma mensagem nova, algo deu errado
(geralmente problema de internet ou de versão do Python — volte na seção 0 e confirme a versão).

**Como confirmar que deu certo:** o comando termina sem nenhuma linha em vermelho tipo `ERROR:`.

---

## 4. Configurar o arquivo `.env`

Esse arquivo guarda informações sensíveis (senha do banco, chave secreta) e **nunca é versionado
no Git** — cada pessoa do time cria o seu próprio, localmente.

1. Copie o modelo:
   ```powershell
   copy .env.example .env
   ```

2. Gere uma chave secreta só sua (com o `(venv)` ativo):
   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(50))"
   ```
   Copie o texto que aparecer.

3. Abra o arquivo `.env` num editor de texto:
   ```powershell
   notepad .env
   ```

4. Preencha assim (substitua os valores entre `<>`):
   ```
   DJANGO_SECRET_KEY=<cole aqui a chave gerada no passo 2>
   DJANGO_DEBUG=True
   DJANGO_SETTINGS_MODULE=config.settings
   DATABASE_URL=<cole aqui a string de conexão que pegou com quem administra o banco>
   ALLOWED_HOSTS=localhost,127.0.0.1
   ```
   O `DATABASE_URL` tem esse formato (exemplo, não use este valor real):
   `postgresql://usuario:senha@host:5432/nome_do_banco?sslmode=require`

5. Salve e feche o Notepad.

**Como confirmar que deu certo:** rode
```powershell
python manage.py migrate
```
Se aparecer uma lista de linhas `Applying <alguma_coisa>... OK`, a conexão com o banco funcionou
e as tabelas foram criadas.

### Erro comum: `TypeError: a bytes-like object is required, not 'str'`

Isso quase sempre significa que o `.env` não existe, está vazio, ou o `DATABASE_URL` não foi
preenchido. Confirme que o arquivo `.env` existe (`dir .env`) e que a linha `DATABASE_URL=...`
tem um valor de verdade, sem espaço nenhum antes/depois do `=`.

---

## 5. Baixar os modelos de reconhecimento facial

Esses são dois arquivos binários (~37MB no total) que **não vêm pelo Git** — cada máquina
precisa baixar na mão, uma vez só.

```powershell
cd resources\models
```

```powershell
Invoke-WebRequest -Uri "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx" -OutFile "face_detection_yunet_2023mar.onnx"

Invoke-WebRequest -Uri "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx" -OutFile "face_recognition_sface_2021dec.onnx"
```

**Como confirmar que deu certo:** rode `dir` e confira os tamanhos:

```
face_detection_yunet_2023mar.onnx      ~230 KB
face_recognition_sface_2021dec.onnx    ~37 MB
```

Se algum arquivo aparecer com só **algumas dezenas de KB**, abra ele com `notepad` — se aparecer
um texto tipo `version https://git-lfs.github.com/...`, o download pegou um "ponteiro" em vez do
arquivo de verdade. Nesse caso, cole o link direto no navegador (Chrome/Edge) em vez de usar o
PowerShell — o download automático do navegador costuma resolver.

Depois de confirmar, volte pra pasta principal do projeto:
```powershell
cd ..\..
```

---

## 6. Testar se tudo está funcionando

Com `(venv)` ativo e na pasta `CampusPark\campuspark`:

```powershell
python manage.py shell
```

Dentro do shell que abrir, cole linha por linha:

```python
from integrations.facial_recognition import FacialRecognition
fr = FacialRecognition()
print("Modelos carregados com sucesso!")
```

**Como confirmar que deu certo:** a última linha imprime `Modelos carregados com sucesso!`. Pode
aparecer algumas linhas `[ WARN:...]` antes disso — são avisos internos do OpenCV sobre otimização
de hardware, **não são erro**, pode ignorar.

Se der `FileNotFoundError`, volte na seção 5 e confirme que os dois `.onnx` estão exatamente em
`campuspark/resources/models/` (não em `resources/models/models/` nem em outra pasta parecida).

Para sair do shell: `exit()`.

---

## 7. Subir o servidor

Ainda com `(venv)` ativo:

```powershell
python manage.py runserver
```

**Como confirmar que deu certo:** aparece uma mensagem tipo
`Starting development server at http://127.0.0.1:8000/`. Abra esse endereço no navegador — deve
carregar uma tela do sistema (não uma página de erro).

Pra parar o servidor: `Ctrl + C` no PowerShell.

---

## Resumo rápido (pra quem já fez uma vez e só quer o "cola aqui")

```powershell
git clone <url-do-repositorio>
cd CampusPark\campuspark
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
notepad .env    # preencher DJANGO_SECRET_KEY e DATABASE_URL
python manage.py migrate
cd resources\models
Invoke-WebRequest -Uri "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx" -OutFile "face_detection_yunet_2023mar.onnx"
Invoke-WebRequest -Uri "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx" -OutFile "face_recognition_sface_2021dec.onnx"
cd ..\..
python manage.py runserver
```

---

## Problemas comuns (tabela rápida)

| Sintoma | Causa provável | Solução |
|---|---|---|
| `python` não é reconhecido | Python não instalado ou não marcou "Add to PATH" | Reinstalar Python marcando a opção no instalador |
| `venv\Scripts\activate` dá erro de módulo não encontrado | Faltou o `.\` na frente, ou usou `activate` em vez de `Activate.ps1` | Use exatamente `.\venv\Scripts\Activate.ps1` |
| "execução de scripts foi desabilitada" | Política de segurança do PowerShell | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| `TypeError: a bytes-like object...` ao rodar `manage.py` | `.env` não existe ou `DATABASE_URL` vazio | Ver seção 4 |
| `FileNotFoundError` nos modelos `.onnx` | Arquivos não baixados ou em pasta errada | Ver seção 5 — confirmar tamanho e local exatos |
| Arquivo `.onnx` com poucos KB e texto estranho dentro | Baixou um ponteiro Git LFS, não o arquivo real | Baixar pelo link direto no navegador |
| Erro relacionado a `opencv-contrib-python` ou `cv2.FaceDetectorYN_create` não existe | Conflito entre `opencv-python` e `opencv-contrib-python` instalados juntos na mesma venv | `pip uninstall opencv-python` e reinstalar só o `opencv-contrib-python` |
| pip trava ou demora muito instalando | Geralmente é o OpenCV baixando (é uma lib grande) ou problema de internet | Aguardar; se passar de 10-15 min parado, cancelar (Ctrl+C) e rodar `pip install -r requirements.txt` de novo |

---

## Regras importantes pra não quebrar o ambiente de ninguém

- **Nunca** dê `git add` no arquivo `.env` nem nos arquivos `.onnx` — ambos já estão no
  `.gitignore`, mas confirme antes de commitar algo suspeito com `git status`.
- Cada pessoa do time cria o próprio `.env` — não copie o `.env` de outra pessoa por e-mail/chat
  sem necessidade (contém senha de banco).
- Se você mudar algo em `requirements.txt`, avise o time — todo mundo vai precisar rodar
  `pip install -r requirements.txt` de novo pra pegar a atualização.
