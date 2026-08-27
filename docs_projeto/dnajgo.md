# Projeto em Django

Um propjeto Django permite a criação de diversos aplicativos em um só proejto.

No contexto do **CampusPark**, criaremos um aplicativo para acesso dos alunos e outro para operadores/gerenciadores internos do sistema



## Instalação

### 1. Instalação
`pip install django`

### 2. Reiniciar computador

### 3. Testar Instalação

`django-admin`
 * Caso não encontre o pacote instalado, tente desisntalar o pacote e realizar o mesmo procedimento.
 * Verifique se o pyathon está inslado e o PATH configurado em suas variáveis de ambiente

### 5. Iniciar projeto

`django-admin startproject campuspark`



## Rodar Projeto

### 1. Mude para pasta do proejto
`cd campuspark`

### 2. Inicie a aplicação
`python manage.py runserver`



## Estrutura Projeto

```text
campuspark/
├── manage.py
└── campuspark/
	├── __init__.py
	├── asgi.py
	├── settings.py
	├── urls.py
	├── wsgi.py
	└── __pycache__/
├── templates/
```



## Reponsabilidade dos Arquivos no projeto

### settings
* Configurações gerais da aplicação

### urls.py
* Define links/caminhos da aplicação

### wsgi.py & asgi.py
* Configura o servidor da aplicação quando for feito deploy do proejto



## Criar Aplicação

### 1. Mude para pasta do proejto
`cd campuspark`

### 2. Crie a nova aplicação
`python manage.py startapp campuspark_aluno`

`python manage.py startapp campuspark_operador`



## Estrutura da Aplicação

### 1. campuspark_aluno

```text
campuspark_aluno/
├── __init__.py
├── admin.py
├── apps.py
├── migrations/
│   └── __init__.py
├── models.py
├── tests.py
├── views.py
└── __pycache__/
```

### 2. campuspark_operador

```text
campuspark_operador/
├── __init__.py
├── admin.py
├── apps.py
├── migrations/
│   └── __init__.py
├── models.py
├── tests.py
└── views.py
```



## Reponsabilidade dos Arquivos nas aplicações

### /migrations
*  Registra as modificações no banco de dados

### admin
* gerencia a tela de administrador do site

### apps 
* Quais apps existem dentro da aplicação

### tests
* Configuração de testes

### models
* Módulos armazenam tudo o que é utilizado no sistema e seu banco de dados

### views
* lógica do site


### (Externo) templates/
* Armazena os tempaltes front-end do site
    * HTML
    * CSS
    * JavaScript
    * ETC