# CampusPark — Modelo de Dados

> Detalhamento das entidades definidas em `arquitetura.md`, com tipos de campo, restrições e
> justificativa de cada decisão. Serve de referência para escrever os `models.py` de cada app
> (código completo em `guia_desenvolvimento.md`).

---

## 1. Diagrama Lógico

```
Aluno 1 ──< Veiculo 1 ──< RegistroAcesso >── 1 Operador >── 1 TipoOperador
```

- Um **Aluno** possui um ou mais **Veículos** (RN04).
- Um **Veículo** possui zero ou mais **RegistroAcesso** (um por evento de entrada/saída).
- Um **Operador** pode estar associado a vários registros de acesso (quem validou a entrada/saída);
  campo opcional, pois no MVP a validação pode ser automática (leitor RFID).
- Um **Operador** possui um **TipoOperador** (ex.: portaria, administrador).

---

## 2. Entidades

### 2.1 Aluno

| Campo | Tipo | Restrições | Observação |
|---|---|---|---|
| id | LONG (identity) | PK | |
| matricula | CHAR(7) | NOT NULL, UNIQUE | RN01 |
| cpf | CHAR(11) | NOT NULL, UNIQUE | |
| nome_completo | VARCHAR(200) | NOT NULL | |
| email_institucional | VARCHAR(64) | NOT NULL | Usado como identificador de login alternativo |
| senha_hash | VARCHAR(255) | NOT NULL | Nunca armazenar senha em texto puro — usar hash do Django (`AbstractBaseUser`) |
| ativo | BOOLEAN | DEFAULT TRUE | Necessário para RF07/RF11 — aluno inativo não pode acessar |
| data_criacao | TIMESTAMP | NOT NULL | `auto_now_add` |

### 2.2 Veiculo

| Campo | Tipo | Restrições | Observação |
|---|---|---|---|
| id | LONG (identity) | PK | |
| aluno_id | LONG | FK → Aluno, NOT NULL | RN04 |
| placa | CHAR(7) | NOT NULL, UNIQUE | RN02 |
| renavam | CHAR(11) | UNIQUE, NULLABLE | |
| tipo | VARCHAR(20) | NOT NULL | carro, moto, etc. |
| fabricante | VARCHAR(30) | NULLABLE | |
| modelo | VARCHAR(30) | NULLABLE | |
| cor | VARCHAR(20) | NULLABLE | |
| tag_rfid | VARCHAR(30) | NOT NULL, UNIQUE | RN03 |
| autorizado | BOOLEAN | DEFAULT TRUE | RF07/RF11 — veículo pode ser desautorizado sem excluir o cadastro |
| data_criacao | TIMESTAMP | NOT NULL | `auto_now_add` |

### 2.3 TipoOperador

| Campo | Tipo | Restrições | Observação |
|---|---|---|---|
| id | INT (identity) | PK | |
| descricao | VARCHAR(30) | NOT NULL | Ex.: "Portaria", "Administrador" |

### 2.4 Operador

| Campo | Tipo | Restrições | Observação |
|---|---|---|---|
| id | LONG (identity) | PK | |
| tipo_operador_id | INT | FK → TipoOperador, NOT NULL | |
| cpf | CHAR(11) | NOT NULL, UNIQUE | |
| nome_completo | VARCHAR(200) | NOT NULL | |
| email | VARCHAR(255) | NOT NULL | |
| data_criacao | TIMESTAMP | NOT NULL | `auto_now_add` |

### 2.5 RegistroAcesso

| Campo | Tipo | Restrições | Observação |
|---|---|---|---|
| id | LONG (identity) | PK | |
| veiculo_id | LONG | FK → Veiculo, NOT NULL, `on_delete=PROTECT` | Impede excluir veículo com histórico |
| operador_id | LONG | FK → Operador, NULLABLE, `on_delete=SET_NULL` | Nulo se validação for automática |
| data_entrada | TIMESTAMP | NOT NULL | `auto_now_add` — RF08 |
| data_saida | TIMESTAMP | NULLABLE | Preenchido só no momento da saída — RF09 |
| status | ENUM | NOT NULL, DEFAULT `DENTRO` | `DENTRO` / `FINALIZADO` / `NEGADO` |

---

## 3. Por que unificar `historico_entrada` + `historico_saida`?

O diagrama ER original enviado pela equipe modela **duas tabelas separadas**:

```
historico_entrada (cd_reg_entrada, id_carro, id_aluno, data_entrada)
historico_saida   (cd_reg_saida, id_carro, id_aluno, data_saida)
```

Essa modelagem tem um problema para a regra **RN05/RN06**: para saber se um veículo já está
"dentro" do estacionamento, seria preciso comparar as duas tabelas (contar entradas sem saída
correspondente), o que é mais caro e mais propenso a bugs de concorrência (dois eventos quase
simultâneos podem gerar dois registros de entrada válidos).

Unificando em **uma única tabela `RegistroAcesso`** com `data_saida` anulável e um campo `status`:

- RN05 vira uma única consulta: `RegistroAcesso.objects.filter(veiculo=X, status="DENTRO").exists()`.
- RN06 vira: buscar o registro `DENTRO` mais recente daquele veículo e fechar (`UPDATE`, não `INSERT`).
- O histórico completo (RF10) continua disponível — é só listar todos os registros do veículo,
  ordenados por `data_entrada`.

Se a equipe decidir manter as duas tabelas separadas (por exemplo, por já estarem no diagrama
aprovado com o professor/orientador), a mesma lógica de validação deve ser replicada consultando
as duas tabelas dentro do `AcessoService` — apenas fica mais verboso.

---

## 4. Índices Recomendados

| Tabela | Índice | Motivo |
|---|---|---|
| Veiculo | `tag_rfid` | Consulta mais frequente do sistema — leitura na portaria (RF06) |
| Veiculo | `placa` | Consulta administrativa (RF12) |
| Aluno | `matricula` | Login e consulta administrativa |
| RegistroAcesso | `(veiculo_id, status)` | Consulta usada em toda validação de entrada/saída (RN05/RN06) |

> Em Django, `unique=True` já cria índice automaticamente. Para o índice composto de
> `RegistroAcesso`, usar `class Meta: indexes = [models.Index(fields=["veiculo", "status"])]`.
