# CampusPark — Guia de Instalação e Uso (do zero)

> Este guia assume que você **nunca configurou esse projeto antes** e não sabe nada de Python,
> Git ou Django. Siga os passos na ordem, sem pular nenhum. Cada seção tem uma parte de
> "Como confirmar que deu certo" — não avance sem confirmar.
>
> Ele tem duas partes:
> - **Parte 1 (seções 0 a 7):** instalar e configurar o ambiente.
> - **Parte 2 (seções 8 a 15):** usar o sistema — do cadastro do aluno até a validação de
>   entrada e saída, incluindo o executável de identificação facial.
>
> Testado em **Windows + PowerShell**. O executável (`.exe`) é **somente Windows**. Se você usa
> Mac/Linux, os comandos de ativar o ambiente mudam um pouco — está marcado onde isso acontece.

---

# PARTE 1 — Instalação

## 0. O que você vai precisar antes de começar

### O que instalar no computador

| O que | Versão | Para que serve | Onde baixar |
|---|---|---|---|
| **Git** | qualquer recente | Baixar o projeto e versionar o código | [git-scm.com](https://git-scm.com/downloads) |
| **Python** | **3.11** ou **3.12** (evite 3.13+) | Roda o sistema (Django) e o reconhecimento facial | [python.org/downloads](https://www.python.org/downloads/) |
| **Navegador** | Chrome ou Edge atualizado | Telas do sistema e câmera do cadastro | — |

Não precisa instalar à mão: Django, OpenCV, PyInstaller e as demais bibliotecas (o `pip` e o
`build_exe.bat` instalam sozinhos, nas seções 3 e 12). Também **não precisa instalar banco de
dados**: o banco é um PostgreSQL na nuvem (Neon).

### O que você precisa ter / pedir

- **Webcam** funcionando (para o cadastro do rosto e para o executável). Sem webcam dá para testar
  com fotos de arquivo — está indicado nas seções 10 e 13.
- Pedir para quem administra o banco (hoje: **Heloisa**) a string de conexão do banco
  (`DATABASE_URL`) — sem isso você não passa do passo 4.
- Acesso ao repositório no GitHub (alguém do time precisa te adicionar como colaborador, ou o
  repositório precisa estar público).
- Cerca de **1 GB livre** em disco (o Python, o OpenCV e o executável gerado ocupam bastante).

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

> Se a instalação parar no pacote `mysqlclient`: o projeto usa PostgreSQL, então ele **não é
> usado**. Veja a tabela de problemas comuns no final deste guia.

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
e as tabelas foram criadas. Esse comando também cria os tipos de operador **"Portaria"** e
**"Administrador"**, usados na seção 8.

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

## 6. Testar se os modelos estão funcionando

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
`Starting development server at http://127.0.0.1:8000/`. Abra `http://localhost:8000/` no
navegador — deve carregar a tela de login do aluno (não uma página de erro).

Pra parar o servidor: `Ctrl + C` no PowerShell.

> **Deixe essa janela do PowerShell aberta** enquanto usa o sistema (Parte 2). Para rodar outros
> comandos, abra **outra** janela do PowerShell, entre em `CampusPark\campuspark` e ative o venv
> de novo (seção 2).

---

# PARTE 2 — Como usar

Visão geral do fluxo completo:

```
Operador admin criado ──> Vagas definidas ──> Aluno se cadastra (com 5 fotos do rosto)
      ──> Aluno cadastra o veículo ──> TAG RFID associada ao veículo (admin)
      ──> Executável identifica o rosto ──> API valida entrada/saída (TAG + rosto)
```

## 8. Criar o usuário do painel `/admin` e o Operador

O sistema tem **dois tipos de login de equipe**, que não são a mesma coisa:

| O que é | Para que serve | Como entra |
|---|---|---|
| **Superusuário** (Django) | Painel técnico `/admin/` — cadastrar operadores, associar TAG ao veículo | Usuário e senha criados no passo abaixo |
| **Operador** (Portaria ou Administrador) | Painel do estacionamento `/operador/` — vagas, histórico, lista de alunos | CPF e senha, cadastrados pelo `/admin/` |

**8.1. Criar o superusuário.** Em uma **segunda** janela do PowerShell (com o venv ativo, na pasta
`CampusPark\campuspark`):

```powershell
python manage.py createsuperuser
```

Informe usuário, e-mail (pode deixar em branco) e senha. A senha não aparece enquanto você digita.

**8.2. Criar o Operador administrador.**

1. Abra `http://localhost:8000/admin/` e entre com o superusuário.
2. Na seção **CAMPUSPARK_USUARIO**, clique em **Adicionar** na linha **Operadors** (é assim que o
   Django escreve o plural).
3. Preencha: **Tipo operador** = `Administrador`, **Cpf** (11 números, sem pontos), **Nome
   completo**, **Email**, **Senha**. Deixe **Ativo** marcado.
4. Clique em **Salvar**.

> Só o tipo **Administrador** pode alterar vagas e editar alunos. O tipo **Portaria** só
> consulta.

**Como confirmar que deu certo:** abra `http://localhost:8000/operador/login/`, entre com o CPF e a
senha do operador e veja o dashboard "Estacionamento".

---

## 9. Definir a capacidade de vagas

Com o operador administrador logado em `http://localhost:8000/operador/`:

1. No bloco **Capacidade do Estacionamento**, informe as vagas de carro e de moto (ex.: 10 e 5).
2. Clique em **Salvar capacidade**.

> **Importante:** o valor padrão é **0 vaga**. Com 0 vaga, **toda entrada é negada** com a
> mensagem "Não há vagas disponíveis para este tipo de veículo".

---

## 10. Cadastro do aluno (com as fotos do rosto)

O rosto é capturado **no próprio cadastro** do aluno. Sem as fotos, o cadastro não é concluído.

1. Abra **`http://localhost:8000/cadastro/`**.
   - Use sempre `localhost` (ou `https://`). Por IP da rede (`http://192.168...`) o navegador
     **bloqueia a câmera**.
2. Preencha **Nome completo**, **Matrícula (RA)** com 7 números, **CPF**, **E-mail
   institucional** e **Senha** (mínimo de 6 caracteres).
3. Na seção **Foto do rosto**, clique em **Ativar câmera** e **permita** o acesso quando o
   navegador perguntar.
4. Fique de frente para a câmera, com boa iluminação e sem boné ou óculos escuros. Clique em
   **Tirar 5 fotos** e fique parado até aparecer "5 fotos capturadas" e as miniaturas.
5. Clique em **Criar minha conta**.

**Como confirmar que deu certo:** você é levado para a tela de cadastro de veículo.

O sistema exige que pelo menos 3 das 5 fotos tenham rosto detectado. Se não conseguir, o cadastro
é recusado (o aluno **não** é criado) e aparece a orientação para tirar as fotos de novo.

**Sem webcam?** Com `DJANGO_DEBUG=True` aparece o link **"Sem câmera? ... enviar fotos do
computador"**. Selecione de 3 a 10 fotos do seu rosto (de frente, bem iluminadas). Em produção
(`DJANGO_DEBUG=False`) esse link some.

> **Alunos cadastrados antes dessa funcionalidade** não têm rosto. Para eles, rode o cadastro por
> linha de comando (precisa de webcam): `python manage.py cadastrar_rosto <matricula>`.

---

## 11. Cadastro do veículo e associação da TAG

**11.1. Cadastrar o veículo (feito pelo aluno).** Logo após o cadastro, na tela de veículo (ou em
`http://localhost:8000/veiculos/novo/`), informe o tipo (automóvel ou motocicleta), a **placa** no
padrão Mercosul (3 letras, 1 número, 1 letra ou número, 2 números — ex.: `ABC1D23`) e o
**modelo/ano**.

**11.2. Associar a TAG RFID (feito pela equipe).** O aluno não preenche a TAG; ela é vinculada
pelo painel técnico:

1. Abra `http://localhost:8000/admin/` e entre com o superusuário.
2. Na seção **CAMPUSPARK_VEICULO**, clique em **Veiculos** e abra o veículo do aluno (pela placa).
3. Preencha **Tag rfid** (ex.: `TAG001`). Cada TAG só pode estar em **um** veículo.
4. Confirme que **Autorizado** está marcado e clique em **Salvar**.

**Como confirmar que deu certo:** o veículo aparece na lista do admin com a TAG preenchida.

---

## 12. Gerar o executável da identificação facial

A identificação por rosto, que antes era um comando no PowerShell, agora é um programa
(`CampusPark_Reconhecimento.exe`). Ele é gerado **uma vez** (e de novo só quando o código mudar).

**Arquivos necessários** (já vêm no projeto, em `CampusPark\campuspark\`):
`reconhecimento_app.py`, `build_exe.bat` e os arquivos `__init__.py` das pastas `apps`,
`apps\campuspark_acesso`, `apps\campuspark_veiculo`, `apps\campuspark_usuario`, `core` e
`integrations`.

**Passos:**

1. Confirme que os modelos `.onnx` estão em `resources\models\` (seção 5) e que o `.env` existe.
2. Dê **duplo clique** em `build_exe.bat`. Ele usa o `venv` do projeto, instala o PyInstaller e
   gera o programa. Leva alguns minutos.
3. Ao final aparece `Pronto: dist\CampusPark_Reconhecimento\CampusPark_Reconhecimento.exe`.

**Onde fica o executável:**
```
CampusPark\campuspark\dist\CampusPark_Reconhecimento\CampusPark_Reconhecimento.exe
```

- Use **sempre a pasta inteira** `CampusPark_Reconhecimento`. O `.exe` depende dos arquivos ao
  lado dele (pasta `_internal` e o `.env`, que o `build_exe.bat` copia para lá).
- A pasta fica grande (~400 MB). Isso é normal.
- O `.env` copiado tem a senha do banco: **não compartilhe** a pasta `dist` com terceiros.
- Adicione `build/`, `dist/` e `*.spec` ao `.gitignore` para não subirem no Git.

**Como confirmar que deu certo:**

```powershell
cd dist\CampusPark_Reconhecimento
.\CampusPark_Reconhecimento.exe --teste
```

Os itens devem aparecer com `[OK]`: banco de dados, modelos faciais e webcam. O número de
"Rostos em memória" deve ser maior que 0 (por causa do cadastro da seção 10).

---

## 13. Rodar a identificação facial

Dê **duplo clique** em `CampusPark_Reconhecimento.exe` (ou rode pelo PowerShell). A webcam abre
numa janela:

- Rosto reconhecido: aparece o **nome** e o **score**, em **verde**.
- Rosto desconhecido: aparece "Nao identificado", em **vermelho**.
- No canto aparece o tempo de cada reconhecimento em milissegundos (a meta é menos de 2 segundos).

**Teclas:** `ESC` ou `Q` fecham | `R` recarrega os rostos do banco. Os rostos também são
recarregados sozinhos a cada 30 segundos, então quem se cadastrou com o programa aberto passa a ser
reconhecido sem reiniciar.

**Opções** (rodando pelo PowerShell, dentro da pasta `dist\CampusPark_Reconhecimento`):

| Comando | O que faz |
|---|---|
| `.\CampusPark_Reconhecimento.exe --teste` | Confere banco, modelos e webcam e sai |
| `.\CampusPark_Reconhecimento.exe --camera 1` | Usa outra webcam (padrão é a `0`) |
| `.\CampusPark_Reconhecimento.exe --imagem C:\caminho\foto.jpg` | Identifica a partir de uma foto, **sem webcam** |

Se der algum problema, a janela fica aberta mostrando a mensagem.

---

## 14. Validar entrada e saída (TAG + rosto)

Hoje o executável **só identifica quem é a pessoa**. A validação em 2 etapas (TAG RFID + rosto) é
feita pela API de acesso, e o `aluno_id` é o resultado do reconhecimento facial. Com o servidor
rodando (seção 7):

**14.1. Descobrir o ID do aluno reconhecido.** Abra
`http://localhost:8000/api/usuario/alunos/` e anote o `id` do aluno.

**14.2. Registrar a ENTRADA** (em uma janela do PowerShell, com o servidor rodando em outra):

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/acesso/entrada/ -ContentType "application/json" -Body '{"tag_rfid":"TAG001","aluno_id":1}'
```

Troque `TAG001` pela TAG do veículo e `1` pelo `id` do aluno.

**Resposta esperada:** o registro com `status: DENTRO`. No PowerShell do servidor aparece
`[CANCELA] Abrindo cancela. Entrada liberada para <placa>.` (a cancela é simulada).

**14.3. Registrar a SAÍDA:**

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/acesso/saida/ -ContentType "application/json" -Body '{"tag_rfid":"TAG001"}'
```

**Resposta esperada:** o registro com `status: FINALIZADO`.

**14.4. Conferir o histórico.** No painel do operador (`http://localhost:8000/operador/`), a tabela
"Histórico de Entrada e Saída" mostra os registros, e os contadores de carros/motos dentro
acompanham.

### Testes que valem a pena fazer

| Teste | Resultado esperado |
|---|---|
| Repetir a entrada com o mesmo veículo | Negado (403): "Este veículo já possui uma entrada em aberto." |
| Entrada com `aluno_id` de **outro** aluno | Negado (403): "O rosto reconhecido não corresponde ao aluno vinculado a esta TAG." |
| Entrada com TAG que não existe | Negado (403): "TAG não encontrada no sistema." |
| Saída sem entrada em aberto | Negado (400): "Não há entrada em aberto para esta TAG." |
| Entrada com as vagas esgotadas | Negado (403): "Não há vagas disponíveis para este tipo de veículo." |

> **Atenção:** se a entrada for enviada **sem** `aluno_id`, ela passa só com a TAG — hoje o rosto
> é opcional na API, e a saída também não confere o rosto.

---

## 15. Rotina do dia a dia (resumo de uso)

Depois que tudo está instalado, para usar o sistema você só precisa de:

1. Abrir o PowerShell em `CampusPark\campuspark`, ativar o venv e rodar:
   ```powershell
   .\venv\Scripts\Activate.ps1
   python manage.py runserver
   ```
2. Abrir `http://localhost:8000/` no navegador (alunos) ou `http://localhost:8000/operador/`
   (equipe).
3. Para identificar rostos, abrir `dist\CampusPark_Reconhecimento\CampusPark_Reconhecimento.exe`.

---

## Resumo rápido (pra quem já fez uma vez e só quer o "cola aqui")

**Instalação:**

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
python manage.py createsuperuser
python manage.py runserver
```

**Uso (em outra janela do PowerShell, com o servidor rodando):**

1. `http://localhost:8000/admin/` → criar **Operador** (tipo Administrador, CPF, senha).
2. `http://localhost:8000/operador/login/` → definir **vagas** (carro e moto).
3. `http://localhost:8000/cadastro/` → cadastrar o aluno **com as 5 fotos** → cadastrar o veículo.
4. `http://localhost:8000/admin/` → Veículos → preencher a **TAG RFID** e manter **Autorizado**.
5. Duplo clique em `build_exe.bat` → `.\CampusPark_Reconhecimento.exe --teste` → abrir o `.exe`.
6. `Invoke-RestMethod` em `/api/acesso/entrada/` e `/api/acesso/saida/` (seção 14).

---

## Problemas comuns (tabela rápida)

| Sintoma | Causa provável | Solução |
|---|---|---|
| `python` não é reconhecido | Python não instalado ou não marcou "Add to PATH" | Reinstalar Python marcando a opção no instalador |
| `venv\Scripts\activate` dá erro de módulo não encontrado | Faltou o `.\` na frente, ou usou `activate` em vez de `Activate.ps1` | Use exatamente `.\venv\Scripts\Activate.ps1` |
| "execução de scripts foi desabilitada" | Política de segurança do PowerShell | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| `TypeError: a bytes-like object...` ao rodar `manage.py` | `.env` não existe ou `DATABASE_URL` vazio | Ver seção 4 |
| `pip install` falha em `mysqlclient` | Esse pacote precisa de compilador no Windows e **não é usado** (o banco é PostgreSQL) | Apagar a linha `mysqlclient>=2.2` do `requirements.txt` e rodar o `pip install -r requirements.txt` de novo (avise o time) |
| `FileNotFoundError` nos modelos `.onnx` | Arquivos não baixados ou em pasta errada | Ver seção 5 — confirmar tamanho e local exatos |
| Arquivo `.onnx` com poucos KB e texto estranho dentro | Baixou um ponteiro Git LFS, não o arquivo real | Baixar pelo link direto no navegador |
| Erro relacionado a `opencv-contrib-python` ou `cv2.FaceDetectorYN_create` não existe | Conflito entre `opencv-python` e `opencv-contrib-python` instalados juntos na mesma venv | `pip uninstall opencv-python` e reinstalar só o `opencv-contrib-python` |
| pip trava ou demora muito instalando | Geralmente é o OpenCV baixando (é uma lib grande) ou problema de internet | Aguardar; se passar de 10-15 min parado, cancelar (Ctrl+C) e rodar `pip install -r requirements.txt` de novo |
| A câmera não liga no cadastro | Página aberta por IP da rede ou `http://` fora do localhost; permissão negada | Abrir por `http://localhost:8000/cadastro/` e permitir a câmera no cadeado da barra de endereço |
| Câmera bloqueada pelo Windows | Privacidade do Windows | Configurações > Privacidade e segurança > Câmera: permitir o acesso (inclusive a apps da área de trabalho) |
| "Não conseguimos detectar seu rosto nas fotos" | Pouca luz, rosto cortado/de lado, boné ou óculos escuros | Refazer as fotos de frente, com boa iluminação, rosto inteiro no quadro |
| "O reconhecimento facial está indisponível no momento" | Modelos `.onnx` ausentes | Ver seção 5 |
| O cadastro volta pedindo as fotos de novo | Houve outro problema no formulário (ex.: RA repetido) e o navegador não reenvia as fotos | Corrigir o campo indicado e tirar as fotos de novo |
| Entrada negada: "Não há vagas disponíveis..." | Capacidade de vagas em 0 (padrão) | Definir as vagas (seção 9) |
| Entrada negada: "TAG não encontrada" | TAG não associada ao veículo | Preencher a TAG no admin (seção 11.2) |
| `build_exe.bat`: "Unable to find ...\build\resources\models" | Versão antiga do `build_exe.bat` | Usar o `build_exe.bat` atualizado (caminhos absolutos) |
| `build_exe.bat` falha com erro de módulo/`NoneType` ao analisar o Django | Faltam os `__init__.py` das pastas `apps`, `core`, `integrations` | Criar os `__init__.py` vazios listados na seção 12 |
| O `.exe` abre e fecha dizendo ".env não encontrado" | `.env` não está na mesma pasta do `.exe` | Copiar o `.env` para `dist\CampusPark_Reconhecimento\` |
| `--teste`: "[FALHA] Webcam 0" | Webcam em uso por outro programa, desligada ou com outro índice | Fechar o outro programa (Teams, Zoom, navegador), ou usar `--camera 1`; sem webcam, use `--imagem` |
| O `.exe` mostra "Nao identificado" para você mesmo | Score abaixo do limiar (0.36) | Cadastrar o rosto de novo com mais luz; use `--imagem` para comparar com uma foto nítida |

---

## Regras importantes pra não quebrar o ambiente de ninguém

- **Nunca** dê `git add` no arquivo `.env` nem nos arquivos `.onnx` — ambos já estão no
  `.gitignore`, mas confirme antes de commitar algo suspeito com `git status`. O mesmo vale para
  as pastas `build/` e `dist/` do executável (têm o `.env` dentro).
- Cada pessoa do time cria o próprio `.env` — não copie o `.env` de outra pessoa por e-mail/chat
  sem necessidade (contém senha de banco).
- Se você mudar algo em `requirements.txt`, avise o time — todo mundo vai precisar rodar
  `pip install -r requirements.txt` de novo pra pegar a atualização.
- Não use o superusuário do `/admin/` como login de operador: são cadastros diferentes (seção 8).
