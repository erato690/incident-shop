"""Fonte simulada: linha do tempo determinística da loja (estado saudável + cenários)."""

import zlib
from datetime import datetime, timedelta
from functools import cache
from random import Random
from statistics import fmean

from api.cenarios import CENARIOS, AnomaliaTabela, Efeito, cenario_em
from api.deploys import DEPLOYS, mensagem_log_deploy
from api.janela import TZ
from api.modelos import (
    CenarioPublico,
    Deploy,
    Janela,
    Metrica,
    Nivel,
    Ponto,
    RegistroLog,
    Resumo,
    SerieMetrica,
    Servico,
    TabelaBanco,
)

SERVICOS = ("pedidos-api", "pagamentos-api", "estoque-worker", "auth-api")
COMUNS = ("requisicoes", "erros_5xx", "latencia_p95", "cpu", "memoria", "reinicios")
METRICAS_DO_SERVICO = {
    "pedidos-api": COMUNS + ("conexoes_db",),
    "pagamentos-api": COMUNS,
    "estoque-worker": COMUNS + ("conexoes_db", "fila_mensagens"),
    "auth-api": COMUNS,
}
UNIDADES = {
    "requisicoes": "req/min", "erros_5xx": "erros/min", "latencia_p95": "ms", "cpu": "%",
    "memoria": "%", "reinicios": "reinícios/min", "conexoes_db": "conexões", "fila_mensagens": "mensagens",
}
# (base, ruído): valor = base ± ruído
BASELINE = {
    "pedidos-api": {"requisicoes": (140, 10), "latencia_p95": (120, 15), "cpu": (35, 5), "memoria": (55, 2)},
    "pagamentos-api": {"requisicoes": (90, 8), "latencia_p95": (180, 20), "cpu": (30, 4), "memoria": (50, 2)},
    "estoque-worker": {"requisicoes": (60, 6), "latencia_p95": (80, 10), "cpu": (20, 3), "memoria": (45, 2), "fila_mensagens": (5, 3)},
    "auth-api": {"requisicoes": (200, 15), "latencia_p95": (60, 8), "cpu": (25, 3), "memoria": (55, 2)},
}
CONEXOES = {"pedidos-api": (4, 7), "estoque-worker": (2, 4)}
MINUTO = timedelta(minutes=1)
# Tabelas do db-principal e os serviços que as usam (ordem fixa).
TABELAS_DB = {
    "pedidos": ("pedidos-api",),
    "itens_pedido": ("pedidos-api",),
    "estoque": ("pedidos-api", "estoque-worker"),
    "reservas_estoque": ("estoque-worker",),
}
SAUDAVEL_DB = AnomaliaTabela((10, 90), (2000, 9000), (5.0, 20.0))


def _tabela_banco(cenario, tabela: str) -> TabelaBanco:
    """Estatísticas da tabela no início do sintoma: saudáveis, salvo anomalia do cenário."""
    a = cenario.banco.get(tabela, SAUDAVEL_DB)
    rng = Random(zlib.crc32(f"{cenario.id}:{tabela}".encode()))
    sequenciais = rng.randint(*a.varreduras_sequenciais)
    por_indice = rng.randint(*a.varreduras_por_indice)
    inchaco = round(rng.uniform(*a.inchaco_indice_pct), 1)
    analyze = cenario.sintoma_inicio.replace(hour=3, minute=0, second=0, microsecond=0)
    return TabelaBanco(
        tabela=tabela, servicos=list(TABELAS_DB[tabela]), varreduras_sequenciais=sequenciais,
        varreduras_por_indice=por_indice, reindexacao_em_andamento=a.reindexacao_em_andamento,
        operacao_em_andamento=a.operacao_em_andamento, ultimo_analyze=analyze, inchaco_indice_pct=inchaco,
    )


def _base(rng: Random, servico: str, metrica: str) -> float:
    if metrica == "erros_5xx":
        return float(rng.randint(0, 1))
    if metrica == "reinicios":
        return 0.0
    if metrica == "conexoes_db":
        return float(rng.randint(*CONEXOES[servico]))
    base, ruido = BASELINE[servico][metrica]
    return round(max(0.0, base + rng.uniform(-ruido, ruido)), 1)


def _info_saudavel(rng: Random, servico: str, minuto: int) -> str:
    if servico == "estoque-worker":
        return f"lote processado: {rng.randint(40, 80)} mensagens"
    return "GET /saude 200"


def _logs_do_minuto(m: datetime, minuto: int, efeito: Efeito, rng: Random) -> list[tuple[int, str, str, str]]:
    brutos: list[tuple[int | None, str, str, str]] = []
    if minuto % 5 == 0:
        for s in SERVICOS:
            if s not in efeito.sem_info_saudavel:
                brutos.append((None, s, "INFO", _info_saudavel(rng, s, minuto)))
    brutos += [(None, d.servico, "INFO", mensagem_log_deploy(d)) for d in DEPLOYS if d.horario == m]
    brutos += [(l.segundo, l.servico, l.nivel, l.mensagem) for l in efeito.logs]
    completos = [(rng.randrange(60) if seg is None else seg, s, n, t) for seg, s, n, t in brutos]
    return sorted(completos, key=lambda x: x[0])


@cache
def _estado_do_minuto(minuto: int):
    """Métricas e logs do minuto (epoch/60). Só depende do minuto: determinístico."""
    m = datetime.fromtimestamp(minuto * 60, TZ)
    cenario = cenario_em(m)
    rng = Random(zlib.crc32(f"{cenario.id if cenario else 'saudavel'}:{minuto}".encode()))
    metricas = {(s, mt): _base(rng, s, mt) for s in SERVICOS for mt in METRICAS_DO_SERVICO[s]}
    efeito = cenario.efeito(cenario, m, rng) if cenario else Efeito()
    metricas.update(efeito.metricas)
    return metricas, _logs_do_minuto(m, minuto, efeito, rng)


def _minuto(m: datetime) -> int:
    return int(m.timestamp() // 60)


def _minutos(inicio: datetime, fim: datetime, arredondar_para_cima: bool):
    """Minutos cheios: logs usam o piso do início; métricas, o teto."""
    primeiro = _minuto(inicio) + (1 if arredondar_para_cima and inicio.second else 0)
    return range(primeiro, _minuto(fim) + (1 if fim.second else 0))


def _serie(servico: str, metrica: str, minutos: range) -> SerieMetrica:
    valores = [_estado_do_minuto(mi)[0][(servico, metrica)] for mi in minutos]
    pontos = [Ponto(horario=datetime.fromtimestamp(mi * 60, TZ), valor=v) for mi, v in zip(minutos, valores)]
    resumo = Resumo(min=min(valores), max=max(valores), media=round(fmean(valores), 1), ultimo=valores[-1])
    return SerieMetrica(servico=servico, metrica=metrica, unidade=UNIDADES[metrica], resumo=resumo, pontos=pontos)


class FonteSimulada:
    nome = "simulada"

    def cenarios(self) -> list[CenarioPublico]:
        return [
            CenarioPublico(
                id=c.id, titulo=c.titulo, servico=c.servico, sintoma_inicio=c.sintoma_inicio,
                janela=Janela(inicio=c.janela_inicio, fim=c.janela_fim),
            )
            for c in CENARIOS
        ]

    def logs(self, servico: Servico | None, nivel: Nivel | None, inicio: datetime, fim: datetime) -> list[RegistroLog]:
        saida = []
        for mi in _minutos(inicio, fim, False):
            base = datetime.fromtimestamp(mi * 60, TZ)
            for seg, s, n, texto in _estado_do_minuto(mi)[1]:
                h = base + timedelta(seconds=seg)
                if inicio <= h < fim and servico in (None, s) and nivel in (None, n):
                    saida.append(RegistroLog(horario=h, servico=s, nivel=n, mensagem=texto))
        return saida

    def metricas(self, servico: Servico | None, metrica: Metrica | None, inicio: datetime, fim: datetime) -> list[SerieMetrica]:
        minutos = _minutos(inicio, fim, True)
        if len(minutos) == 0:
            return []
        return [
            _serie(s, mt, minutos)
            for s in SERVICOS if servico in (None, s)
            for mt in METRICAS_DO_SERVICO[s] if metrica in (None, mt)
        ]

    def deploys(self, servico: Servico | None, inicio: datetime | None, fim: datetime | None) -> list[Deploy]:
        return [
            d for d in DEPLOYS
            if servico in (None, d.servico) and (inicio is None or d.horario >= inicio) and (fim is None or d.horario < fim)
        ]

    def estatisticas_banco(self, cenario: str, servico: Servico | None) -> list[TabelaBanco]:
        c = next(c for c in CENARIOS if c.id == cenario)
        return [
            _tabela_banco(c, t) for t, usuarios in TABELAS_DB.items() if servico is None or servico in usuarios
        ]
