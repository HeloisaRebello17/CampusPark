# CampusPark — Decisões Técnicas (ADRs)

> Registro das principais decisões de arquitetura tomadas no projeto, o porquê de cada uma e as
> alternativas consideradas. Adicione uma nova entrada sempre que uma decisão estrutural for tomada
> (troca de biblioteca, mudança de padrão, etc.) — isso evita que a mesma discussão se repita meses
> depois e ajuda quem entra no time a entender o "porquê", não só o "como".

Formato de cada ADR: **Contexto → Decisão → Alternativas consideradas → Consequências**.

---

## ADR-001 — Framework web: Django (em vez de ASP.NET Core / .NET)

**Contexto:** O relatório do PAC Extensionista apresentado à Católica SC definiu inicialmente a
stack **C# / .NET / ASP.NET Core / EF Core**, alinhada ao restante do ecossistema de sistemas da
área. Na prática, a equipe optou por implementar o MVP em **Python/Django**.

**Decisão:** Seguir com Django + Django REST Framework para o desenvolvimento do MVP e das
próximas fases.

**Alternativas consideradas:**
- ASP.NET Core + EF Core (stack originalmente planejada no relatório do PAC).
- Flask (mais leve, mas exigiria montar manualmente ORM, admin e autenticação que o Django já entrega prontos).

**Consequências:**
- Ganha-se velocidade de desenvolvimento para o MVP: Django Admin pronto para RF15 (administração),
  ORM maduro, autenticação e permissões nativas para RNF14.
- Perde-se a uniformidade com outros sistemas da equipe eventualmente construídos em .NET — caso o
  projeto seja futuramente integrado a sistemas institucionais em C#, será necessário expor/consumir
  API REST em vez de compartilhar código diretamente.
- O relatório formal do PAC deve ser atualizado para refletir a stack real utilizada (divergência
  entre o documento entregue à instituição e a implementação).

---

## ADR-002 — Unificação de `historico_entrada` / `historico_saida` em `RegistroAcesso`

**Contexto:** O diagrama ER inicial modelava entrada e saída como duas tabelas independentes.

**Decisão:** Usar uma única tabela `RegistroAcesso` com `data_saida` anulável e um campo `status`
(`DENTRO` / `FINALIZADO` / `NEGADO`).

**Alternativas consideradas:**
- Manter as duas tabelas separadas, replicando a lógica de validação (RN05/RN06) em duas consultas.

**Consequências:**
- Validação de "veículo já dentro" (RN05) e "saída sem entrada aberta" (RN06) fica mais simples e
  com menor risco de condição de corrida.
- Justificativa completa e comparação lado a lado em `modelo_dados.md`, seção 3.

---

## ADR-003 — Regra de negócio isolada em `services.py`, fora das views

**Contexto:** Views Django/DRF tendem a acumular lógica de negócio junto com tratamento de HTTP,
dificultando testes unitários e reuso (ex.: a mesma validação de entrada pode um dia ser chamada
por um endpoint REST e por um comando de terminal usado em testes de hardware).

**Decisão:** Toda regra de negócio (RN01–RN07) vive em uma classe de serviço (`AcessoService`,
etc.), e a view apenas recebe a requisição, chama o serviço e formata a resposta.

**Alternativas consideradas:**
- Regra de negócio direto na view (mais rápido de escrever, mas difícil de testar isoladamente e
  de reaproveitar em outro ponto de entrada).
- Regra de negócio em métodos do próprio model (`fat models`) — descartado porque a validação de
  entrada envolve múltiplas entidades (Veiculo + Aluno + RegistroAcesso), o que não se encaixa bem
  como método de um único model.

**Consequências:**
- Testes de regra de negócio não dependem de subir servidor HTTP nem de framework de request/response.
- Views ficam mais simples e uniformes entre os apps.

---

## ADR-004 — Simulação de hardware (RFID, câmera, reconhecimento facial) na camada `integrations/`

**Contexto:** O MVP não inclui hardware físico (leitor RFID real, câmera de reconhecimento facial),
conforme escopo definido no documento de MVP — "fora do primeiro MVP".

**Decisão:** Isolar toda a comunicação com hardware em `integrations/` (`rfid_reader.py`,
`camera.py`, `facial_recognition.py`), com uma implementação simulada (`input()`/mock) que respeita
a mesma interface que a implementação real usará depois.

**Alternativas consideradas:**
- Deixar chamadas de simulação espalhadas dentro das views/services — descartado porque tornaria a
  troca para hardware real (fase futura) uma mudança espalhada por vários arquivos, em vez de
  concentrada em um único módulo.

**Consequências:**
- Trocar a simulação pelo SDK real do leitor/câmera, no futuro, deve exigir mudança apenas dentro
  de `integrations/`, sem tocar em `apps/acesso`.

---

## ADR-005 — Estrutura de apps agrupada em `apps/`

**Contexto:** A estrutura inicial tinha os apps Django (`campuspark_usuario`, `campuspark_veiculo`,
`campuspark_acesso`) soltos na raiz do projeto, junto com `config/`, `core/` e `integrations/`.

**Decisão:** Agrupar todos os apps de domínio dentro de uma pasta `apps/`, removendo o prefixo
`campuspark_` do nome (já implícito no repositório).

**Alternativas consideradas:**
- Manter apps soltos na raiz (como estava) — funciona para 3 apps, mas tende a poluir a raiz do
  projeto conforme novos apps forem adicionados nas fases futuras (reconhecimento facial,
  relatórios, notificações).

**Consequências:**
- `INSTALLED_APPS` referencia `apps.usuario`, `apps.veiculo`, `apps.acesso` — necessário garantir
  `apps/__init__.py` e configurar `AppConfig.name` corretamente em cada `apps.py`.

---

## ADR-006 — Login de Operador (porteiro/administrador) e dashboard com controle de vagas

**Contexto:** O documento de requisitos (seção 5, "Fora do Escopo do MVP") e o guia de
desenvolvimento (seção 6) listam explicitamente "dashboard avançado" e "controle de vagas em tempo
real" como fora do primeiro MVP. Ao mesmo tempo, RF15 exige que administradores gerenciem usuários,
veículos, permissões e acessos, e RNF14 exige controle de acesso por perfil (administrador,
operador, usuário comum) — o que pressupõe um login para esses perfis, ainda não implementado.

**Decisão:** Implementar (1) login de `Operador` (perfis "Portaria" e "Administrador", via
`TipoOperador` já modelado) com sessão própria (`request.session`), e (2) uma tela inicial
("dashboard") pós-login mostrando: quantidade de carros/motos atualmente dentro do estacionamento
(derivada de `RegistroAcesso` com `status=DENTRO`), capacidade máxima configurável de vagas por tipo
de veículo (novo model `ConfiguracaoEstacionamento`, edição restrita a Administrador) e o histórico
de entrada/saída (RF10). Essa decisão foi tomada sob pedido explícito do usuário do projeto,
ciente da divergência com o escopo documentado do MVP.

Como pré-requisito, o model `Veiculo` (até então incompleto em relação ao `modelo_dados.md`) foi
completado com os campos já documentados (`tipo`, `tag_rfid`, `autorizado`, `renavam`, `fabricante`,
`modelo`, `cor`, `data_criacao`) — sem isso não é possível diferenciar carro/moto no dashboard, nem
o `AcessoService` (que já referenciava `tag_rfid`/`autorizado`) funcionava de fato.

**Alternativas consideradas:**
- Manter o escopo estritamente como documentado (sem dashboard nem controle de vagas), implementando
  apenas o login de operador — descartada por pedido explícito do usuário.

**Consequências:**
- `apps/usuario` ganha `senha_hash` e `ativo` em `Operador` (login e desativação de conta,
  espelhando o padrão já usado em `Aluno`).
- `apps/acesso` ganha o model `ConfiguracaoEstacionamento` (capacidade máxima por tipo de veículo)
  e as views `DashboardView`/`AtualizarVagasView`.
- `requisitos.md` (seção 5) e `guia_desenvolvimento.md` (seção 6) devem ser lidos com a ressalva de
  que login de operador e dashboard básico de vagas **deixaram de estar fora de escopo** a partir
  desta decisão; "dashboard avançado" (gráficos, relatórios) e integração real com sensores de vaga
  continuam fora do MVP.
