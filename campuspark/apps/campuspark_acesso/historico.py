# historico.py
# Filtros e exportação CSV do histórico de acessos (RF10, RF12).
# Usado pela tela de histórico do operador e pelo relatório mensal do aluno.

import csv
import io
from datetime import date

from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone

from apps.campuspark_veiculo.models import TipoVeiculo
from .models import RegistroAcesso, StatusAcesso


def _data_ou_none(texto: str):
    try:
        return date.fromisoformat(texto) if texto else None
    except ValueError:
        return None


def filtrar_registros(registros, params):
    """Aplica os filtros da tela de histórico. Retorna (registros, filtros, erros);
    filtros inválidos são ignorados e geram uma mensagem em erros."""
    filtros = {
        "data_inicio": params.get("data_inicio", "").strip(),
        "data_fim": params.get("data_fim", "").strip(),
        "busca": params.get("busca", "").strip(),
        "status": params.get("status", ""),
        "tipo": params.get("tipo", ""),
        "origem": params.get("origem", ""),
        "liberacao": params.get("liberacao", ""),
    }
    erros = []

    inicio = _data_ou_none(filtros["data_inicio"])
    fim = _data_ou_none(filtros["data_fim"])
    if (filtros["data_inicio"] and inicio is None) or (filtros["data_fim"] and fim is None):
        erros.append("Data inválida: use o seletor de data.")
    if inicio and fim and inicio > fim:
        erros.append("A data inicial não pode ser depois da data final.")
        inicio = fim = None

    if inicio:
        registros = registros.filter(data_entrada__date__gte=inicio)
    if fim:
        registros = registros.filter(data_entrada__date__lte=fim)
    if filtros["busca"]:
        registros = registros.filter(
            RegistroAcesso.q_placa(filtros["busca"], contem=True)
            | Q(veiculo__aluno__nome_completo__icontains=filtros["busca"])
            | Q(veiculo__aluno__matricula__icontains=filtros["busca"])
            | Q(nome_visitante__icontains=filtros["busca"])
        )
    if filtros["status"] in StatusAcesso.values:
        registros = registros.filter(status=filtros["status"])
    if filtros["origem"] == "visitante":
        registros = registros.filter(veiculo__isnull=True)
    elif filtros["origem"] == "cadastrado":
        registros = registros.filter(veiculo__isnull=False)
    if filtros["liberacao"] == "manual":
        registros = registros.filter(liberacao_manual=True)
    elif filtros["liberacao"] == "automatica":
        registros = registros.filter(liberacao_manual=False)
    if filtros["tipo"] in TipoVeiculo.values:
        registros = registros.filter(RegistroAcesso.q_tipo(filtros["tipo"]))

    return registros, filtros, erros


def formatar_permanencia(delta) -> str:
    minutos = int(delta.total_seconds() // 60)
    horas, minutos = divmod(minutos, 60)
    if horas >= 24:
        dias, horas = divmod(horas, 24)
        return f"{dias}d {horas}h {minutos:02d}min"
    if horas:
        return f"{horas}h {minutos:02d}min"
    return f"{minutos}min"


def _data_hora(dt) -> str:
    return timezone.localtime(dt).strftime("%d/%m/%Y %H:%M") if dt else ""


# Colunas de cada CSV: (cabeçalho, função que extrai o valor do RegistroAcesso).
COLUNAS_ALUNO = [
    ("Placa", lambda r: r.placa_exibicao),
    ("Entrada", lambda r: _data_hora(r.data_entrada)),
    ("Saída", lambda r: _data_hora(r.data_saida)),
    ("Status", lambda r: r.get_status_display()),
]

COLUNAS_OPERADOR = [
    ("Nome", lambda r: r.nome_exibicao),
    ("Matrícula", lambda r: r.matricula_exibicao),
    ("Origem", lambda r: "Visitante" if r.eh_visitante else "Cadastrado"),
    ("Documento (visitante)", lambda r: r.documento_visitante),
    ("Placa", lambda r: r.placa_exibicao),
    ("Tipo", lambda r: r.tipo_exibicao),
    ("Entrada", lambda r: _data_hora(r.data_entrada)),
    ("Saída", lambda r: _data_hora(r.data_saida)),
    ("Permanência", lambda r: formatar_permanencia(r.permanencia)),
    ("Status", lambda r: r.get_status_display()),
    ("Liberação", lambda r: "Manual" if r.liberacao_manual else "Automática"),
    ("Motivo", lambda r: r.motivo),
    ("Operador", lambda r: r.operador.nome_completo if r.operador else ""),
]


def _celula_segura(valor) -> str:
    """Evita injeção de fórmula ao abrir o CSV no Excel (nome começando com '=', '+', ...)."""
    valor = str(valor)
    return "'" + valor if valor[:1] in ("=", "+", "-", "@") else valor


def resposta_csv(registros, nome_arquivo: str, colunas) -> HttpResponse:
    # Monta o arquivo inteiro antes: com charset utf-8-sig, cada write() no HttpResponse
    # ganharia o seu próprio BOM, sujando o início de todas as linhas.
    conteudo = io.StringIO()
    writer = csv.writer(conteudo, delimiter=";")
    writer.writerow([cabecalho for cabecalho, _ in colunas])
    for registro in registros:
        writer.writerow([_celula_segura(extrair(registro)) for _, extrair in colunas])

    response = HttpResponse(conteudo.getvalue(), content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = f'attachment; filename="{nome_arquivo}"'
    return response
