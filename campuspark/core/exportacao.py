import logging
import math
import time

from django.conf import settings
from django.core.cache import cache
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import mark_safe

logger = logging.getLogger("campuspark.exportacao")


class ExportacaoBloqueada(Exception):
    """A exportação foi negada; `segundos` diz quanto falta para poder exportar de novo.

    `modelo` é o texto do aviso com "{tempo}" no lugar do tempo restante:
      - str(erro) traz o texto pronto (log e testes);
      - erro.como_html() traz o tempo num <span data-contagem>, que o static/js/ui.js
        transforma em contagem regressiva na tela."""

    def __init__(self, modelo: str, segundos: int):
        self.modelo = modelo
        self.segundos = segundos
        super().__init__(modelo.replace("{tempo}", tempo_restante(segundos)))

    def como_html(self):
        contagem = format_html(
            '<span class="contagem" data-contagem="{}">{}</span>',
            self.segundos, tempo_restante(self.segundos),
        )
        antes, _, depois = self.modelo.partition("{tempo}")
        return mark_safe(conditional_escape(antes) + contagem + conditional_escape(depois))


def _config(nome: str):
    return getattr(settings, nome)


def _tempo_legivel(segundos: int) -> str:
    if segundos < 60:
        return f"{segundos} segundo{'s' if segundos != 1 else ''}"
    minutos = math.ceil(segundos / 60)
    return f"{minutos} minuto{'s' if minutos != 1 else ''}"


def tempo_restante(segundos: int) -> str:
    """Formato da contagem regressiva: "25 segundos" ou "14 min 05 s".
    Deve ser igual ao formatarTempo() do static/js/ui.js."""
    if segundos < 60:
        return f"{segundos} segundo{'s' if segundos != 1 else ''}"
    minutos, segundos = divmod(segundos, 60)
    return f"{minutos} min {segundos:02d} s"


def ip_do_request(request) -> str:
    """IP de quem fez a requisição.

    Por padrão usa REMOTE_ADDR: o header X-Forwarded-For pode ser enviado por qualquer um e
    serviria para burlar a trava. Só com EXPORTACAO_CONFIAR_PROXY=True (sistema atrás de um
    proxy reverso confiável) é usado o último IP do X-Forwarded-For, que é o adicionado pelo proxy."""
    if _config("EXPORTACAO_CONFIAR_PROXY"):
        encaminhado = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ips = [ip.strip() for ip in encaminhado.split(",") if ip.strip()]
        if ips:
            return ips[-1]
    return request.META.get("REMOTE_ADDR", "") or "desconhecido"


def _verificar(chave: str, agora: float, *, intervalo: int, maximo: int, quem: str) -> list:
    """Aplica as regras a um contador (de um usuário ou de um IP). Retorna os horários das
    exportações ainda dentro da janela ou levanta ExportacaoBloqueada."""
    janela = int(_config("EXPORTACAO_JANELA"))
    bloqueio = int(_config("EXPORTACAO_BLOQUEIO"))

    # 1) Bloqueado por ter passado do limite.
    bloqueado_ate = cache.get(f"{chave}:bloqueio")
    if bloqueado_ate and bloqueado_ate > agora:
        restante = math.ceil(bloqueado_ate - agora)
        raise ExportacaoBloqueada(
            f"Exportação bloqueada por excesso de tentativas {quem}. "
            "Tente novamente em {tempo}.",
            restante,
        )

    # Só os horários de exportação que ainda estão dentro da janela contam.
    historico = [t for t in cache.get(f"{chave}:historico", []) if t > agora - janela]

    # 2) Trava por tempo: intervalo mínimo desde a última exportação.
    if intervalo and historico and agora - historico[-1] < intervalo:
        restante = math.ceil(intervalo - (agora - historico[-1]))
        raise ExportacaoBloqueada(
            "Aguarde {tempo} antes de exportar novamente.", restante,
        )

    # 3) Limite por janela: estourou, bloqueia.
    if len(historico) >= maximo:
        cache.set(f"{chave}:bloqueio", agora + bloqueio, timeout=bloqueio)
        cache.delete(f"{chave}:historico")
        logger.warning(
            "Exportação BLOQUEADA (%s): %s exportações em %ss; bloqueado por %ss.",
            chave, len(historico), janela, bloqueio,
        )
        raise ExportacaoBloqueada(
            f"Limite de {maximo} exportações em {_tempo_legivel(janela)} atingido {quem}. "
            "Exportação bloqueada, tente novamente em {tempo}.",
            bloqueio,
        )

    return historico


def registrar_exportacao(perfil: str, usuario_id, ip: str, descricao: str = "") -> None:
    """Libera (e registra) a exportação ou levanta ExportacaoBloqueada.

    Há dois contadores e os dois precisam liberar:
      - por usuário: intervalo mínimo + limite EXPORTACAO_MAX_POR_JANELA;
      - por IP: limite EXPORTACAO_IP_MAX_POR_JANELA, que pega várias contas no mesmo computador.
        Não tem intervalo mínimo, para operadores na mesma rede não travarem uns aos outros.
    perfil: "operador" ou "aluno" — separa os contadores mesmo que os IDs coincidam.
    descricao: o que foi exportado, só para o log de auditoria."""
    agora = time.time()
    chave_usuario = f"exportacao:usuario:{perfil}:{usuario_id}"
    chave_ip = f"exportacao:ip:{ip}"

    try:
        historico_usuario = _verificar(
            chave_usuario, agora, quem="deste usuário",
            intervalo=int(_config("EXPORTACAO_INTERVALO_MINIMO")),
            maximo=int(_config("EXPORTACAO_MAX_POR_JANELA")),
        )
        historico_ip = _verificar(
            chave_ip, agora, quem="deste endereço de rede",
            intervalo=0,
            maximo=int(_config("EXPORTACAO_IP_MAX_POR_JANELA")),
        )
    except ExportacaoBloqueada:
        logger.warning("Exportação negada: %s id=%s ip=%s %s", perfil, usuario_id, ip, descricao)
        raise

    # Só conta depois que os dois contadores liberaram.
    janela = int(_config("EXPORTACAO_JANELA"))
    cache.set(f"{chave_usuario}:historico", historico_usuario + [agora], timeout=janela)
    cache.set(f"{chave_ip}:historico", historico_ip + [agora], timeout=janela)
    logger.info("Exportação liberada: %s id=%s ip=%s %s", perfil, usuario_id, ip, descricao)
