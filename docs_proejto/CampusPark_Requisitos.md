# CampusPark — Requisitos

> Requisitos levantados junto ao Pró-Reitor da Católica SC, Sr. Bruno Dala, e formalizados no
> documento de especificação do projeto. Servem de base para toda regra de negócio implementada
> em `apps/acesso`, `apps/veiculo` e `apps/usuario` (ver `arquitetura.md`).

---

## 1. Requisitos Funcionais

| Código | Descrição |
|---|---|
| **RF01** | Cadastro de usuários autorizados, contendo no mínimo: nome, número de matrícula, vínculo com a universidade, placa do veículo |
| **RF02** | Registro de um ou mais veículos vinculados a um usuário autorizado |
| **RF03** | Geração automática de QR Code para cada veículo cadastrado e autorizado |
| **RF04** | QR Code gerado obrigatoriamente com base em placa do veículo + número de matrícula do usuário |
| **RF05** | Associação de cada QR Code a um usuário e a um veículo específico |
| **RF06** | Leitura do QR Code/TAG na entrada do estacionamento para validar o acesso |
| **RF07** | Na leitura, verificar: usuário ativo, veículo autorizado, dados coerentes com o banco |
| **RF08** | Registro de data e hora de entrada de cada veículo autorizado |
| **RF09** | Registro de data e hora de saída do veículo, quando aplicável |
| **RF10** | Histórico de acessos contendo: usuário, matrícula, placa, data/hora de entrada e saída |
| **RF11** | Bloqueio de entrada para QR Code/TAG inválido, inexistente, duplicado, vencido ou de cadastro inativo |
| **RF12** | Consulta de usuários cadastrados, veículos vinculados e histórico de acessos |
| **RF13** | Atualização cadastral de usuário e veículo, incluindo placa e situação de autorização |
| **RF14** | Regeneração do QR Code quando houver alteração de placa, matrícula ou situação do cadastro |
| **RF15** | Administradores gerenciam usuários, veículos, permissões e acessos |
| **RF16** | Mensagens de erro/alerta quando houver inconsistência entre QR Code/TAG e dados cadastrados |

## 2. Requisitos Não Funcionais

| Código | Descrição |
|---|---|
| **RNF01** | Segurança dos dados de usuários e veículos contra acessos não autorizados |
| **RNF02** | Integridade dos dados usados na geração e validação do QR Code/TAG |
| **RNF03** | Validação na entrada em tempo hábil (poucos segundos), evitando filas |
| **RNF04** | Disponibilidade durante os horários de funcionamento da universidade e do estacionamento |
| **RNF05** | Interface simples e intuitiva para operadores e administradores |
| **RNF06** | Confiabilidade no registro de acessos, minimizando falhas de leitura/armazenamento |
| **RNF07** | Escalabilidade para crescimento de usuários, veículos e registros de acesso |
| **RNF08** | Manutenibilidade — desenvolvimento modular, facilitando correções e expansões |
| **RNF09** | Compatibilidade com leitores de QR Code/RFID e dispositivos de controle de acesso |
| **RNF10** | Auditoria — rastreabilidade de cadastro, alteração, exclusão e validação de acessos |
| **RNF11** | Confidencialidade de matrícula e placa, respeitando a privacidade dos usuários (LGPD) |
| **RNF12** | Backup e recuperação de dados |
| **RNF13** | Tempo de resposta rápido e estável em consultas/operações administrativas |
| **RNF14** | Controle de acesso por perfil: administrador, operador ou usuário comum |

## 3. Regras de Negócio (definidas no MVP)

| Código | Descrição | Onde é validada |
|---|---|---|
| **RN01** | A matrícula do aluno deve ser única | `Aluno.matricula` (`unique=True`) |
| **RN02** | A placa do veículo deve ser única | `Veiculo.placa` (`unique=True`) + `apps/veiculo/validators.py` |
| **RN03** | Uma TAG RFID não pode estar associada a mais de um veículo | `Veiculo.tag_rfid` (`unique=True`) + `validar_tag_unica()` |
| **RN04** | Todo veículo deve estar associado a um aluno | `Veiculo.aluno` (FK obrigatória) |
| **RN05** | Um veículo já dentro do estacionamento não pode registrar nova entrada | `AcessoService.validar_entrada()` |
| **RN06** | Só é possível registrar saída de um veículo com entrada em aberto | `AcessoService.registrar_saida()` |
| **RN07** | A entrada só é autorizada após identificação da TAG e validação de identidade | `AcessoService.validar_entrada()` (veículo autorizado + aluno ativo) |

## 4. Escopo do MVP

| Área | Funcionalidades |
|---|---|
| Tela do aluno | Login por matrícula e senha; visualização dos dados; cadastro/alteração de veículo; associação da TAG RFID |
| Tela de veículo | Cadastro de placa, tipo, TAG RFID e aluno proprietário |
| Tela de segurança | Identificação pela TAG RFID, validação do veículo, autorização de entrada, registro de entrada e saída |
| Reconhecimento facial | Interface e fluxo preparados; validação **simulada** nesta primeira versão |
| Administrador | CRUD básico de alunos e veículos (cadastro, consulta, alteração, exclusão) |

## 5. Fora do Escopo do MVP

Reconhecimento facial real, integração física com leitor RFID, dashboard avançado, relatórios,
notificações, aplicativo mobile, controle de vagas em tempo real e integrações externas.

## 6. Critério de Conclusão do MVP

O MVP é considerado concluído quando for possível: cadastrar um aluno e seu veículo, associar
uma TAG RFID, realizar login, identificar o veículo, validar o acesso, registrar a entrada e,
posteriormente, registrar a saída — com todos os dados persistidos no banco.
