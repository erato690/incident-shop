"""Catálogo dos 8 cenários de incidente na linha do tempo única da loja (outubro de 2026).

Cada cenário tem janela e sintoma em datas absolutas (-03:00) e uma função `efeito` que diz
o que muda num minuto. A causa raiz é o gabarito: nunca sai pela API.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from random import Random

from api.janela import TZ

MINUTO = timedelta(minutes=1)


@dataclass
class LogEfeito:
    servico: str
    nivel: str
    mensagem: str
    segundo: int | None = None  # None: sorteado pela fonte


@dataclass
class Efeito:
    """O que o cenário muda num minuto, sobre o estado saudável."""

    logs: list[LogEfeito] = field(default_factory=list)
    metricas: dict[tuple[str, str], float] = field(default_factory=dict)
    sem_info_saudavel: set[str] = field(default_factory=set)


@dataclass
class AnomaliaTabela:
    """Estado anormal de uma tabela do db-principal no início do sintoma (faixas inclusivas)."""

    varreduras_sequenciais: tuple[int, int]
    varreduras_por_indice: tuple[int, int]
    inchaco_indice_pct: tuple[float, float]
    operacao_em_andamento: str | None = None

    @property
    def reindexacao_em_andamento(self) -> bool:
        return bool(self.operacao_em_andamento and self.operacao_em_andamento.startswith("REINDEX"))


@dataclass
class Cenario:
    id: str
    titulo: str
    servico: str
    janela_inicio: datetime
    janela_fim: datetime
    sintoma_inicio: datetime
    sintoma_fim: datetime
    causa_raiz: str
    efeito: Callable[["Cenario", datetime, Random], Efeito]
    # tabela do db-principal -> estado anormal; as demais tabelas aparecem saudáveis
    banco: dict[str, AnomaliaTabela] = field(default_factory=dict)


def _t(dia: int, hora: int, minuto: int) -> datetime:
    return datetime(2026, 10, dia, hora, minuto, tzinfo=TZ)


def _k(c: Cenario, m: datetime) -> int:
    """Minutos desde o início do sintoma."""
    return int((m - c.sintoma_inicio) / MINUTO)


def _ativo(c: Cenario, m: datetime) -> bool:
    return c.sintoma_inicio <= m < c.sintoma_fim


def _f(valor: float) -> float:
    return round(float(valor), 1)


HIKARI = (
    "HikariPool-1 - Connection is not available, request timed out after 3000ms "
    "(total=10, active=10, idle=0, waiting={n})\n"
    "\tat com.zaxxer.hikari.pool.HikariPool.createTimeoutException(HikariPool.java:696)\n"
    "\tat br.loja.pedidos.PedidoRepository.salvar(PedidoRepository.java:57)"
)


def _pool_esgotado(c: Cenario, m: datetime, rng: Random) -> Efeito:
    e = Efeito()
    if m < c.sintoma_inicio:  # tráfego crescendo, ainda saudável
        p = (m - c.janela_inicio) / (c.sintoma_inicio - c.janela_inicio)
        e.metricas[("pedidos-api", "requisicoes")] = _f(140 * (1 + 0.4 * p) + rng.uniform(-5, 5))
        e.metricas[("pedidos-api", "conexoes_db")] = float(rng.randint(4, 5 + int(2 * p)))
        return e
    e.metricas[("pedidos-api", "requisicoes")] = _f(140 * rng.uniform(1.4, 2.0))
    e.metricas[("pedidos-api", "conexoes_db")] = 10.0
    e.metricas[("pedidos-api", "latencia_p95")] = float(rng.randint(2500, 5200))
    e.metricas[("pedidos-api", "erros_5xx")] = float(rng.randint(18, 40))
    primeiro = _k(c, m) == 0
    for i in range(rng.randint(6, 13)):
        waiting = 41 if primeiro and i == 0 else rng.randint(12, 60)
        segundo = (7 if i == 0 else rng.randint(8, 59)) if primeiro else None
        e.logs.append(LogEfeito("pedidos-api", "ERROR", HIKARI.format(n=waiting), segundo))
    return e


def _banco_lento(c: Cenario, m: datetime, rng: Random) -> Efeito:
    e = Efeito()
    reindexacao = _t(8, 15, 40)
    if not reindexacao <= m < c.sintoma_fim:
        return e
    espera = 30 + 60 * int((m - reindexacao) / MINUTO)
    e.logs.append(LogEfeito(
        "estoque-worker", "WARN",
        f"lock wait na tabela estoque há {espera}s (reindexação da tabela estoque em andamento no db-principal: "
        "REINDEX TABLE estoque)",
    ))
    if m < c.sintoma_inicio:
        return e
    for servico in ("pedidos-api", "estoque-worker"):
        for _ in range(rng.randint(3, 8)):
            e.logs.append(LogEfeito(
                servico, "ERROR",
                "org.postgresql.util.PSQLException: ERROR: canceling statement due to statement timeout "
                "(query: UPDATE estoque SET reservado = reservado + $1 WHERE sku = $2)",
            ))
        e.metricas[(servico, "latencia_p95")] = float(rng.randint(2000, 6000))
        e.metricas[(servico, "erros_5xx")] = float(rng.randint(15, 30))
    return e


def _deploy_com_bug(c: Cenario, m: datetime, rng: Random) -> Efeito:
    e = Efeito()
    if not _ativo(c, m):
        return e
    for _ in range(rng.randint(8, 20)):
        e.logs.append(LogEfeito(
            "pagamentos-api", "ERROR",
            'java.lang.NullPointerException: Cannot invoke "Cupom.getDesconto()" because "cupom" is null\n'
            "\tat br.loja.pagamentos.PagamentoService.confirmar(PagamentoService.java:88)\n"
            "\tat br.loja.pagamentos.PagamentoController.post(PagamentoController.java:41)",
        ))
    e.metricas[("pagamentos-api", "erros_5xx")] = float(rng.randint(25, 45))
    e.logs.append(LogEfeito(
        "pedidos-api", "WARN",
        "pagamentos-api respondeu 500 em POST /pagamentos, pedido marcado como PENDENTE",
    ))
    return e


def _env_var_faltando(c: Cenario, m: datetime, rng: Random) -> Efeito:
    e = Efeito()
    if m >= c.sintoma_fim:
        return _recuperacao_worker(c, m)
    if not _ativo(c, m):
        return e
    k = _k(c, m)
    e.sem_info_saudavel.add("estoque-worker")
    e.metricas[("estoque-worker", "requisicoes")] = 0.0
    e.metricas[("estoque-worker", "conexoes_db")] = 0.0
    e.metricas[("estoque-worker", "reinicios")] = 1.0
    e.metricas[("estoque-worker", "fila_mensagens")] = float(5 + 120 * (k + 1))
    e.logs.append(LogEfeito(
        "estoque-worker", "ERROR",
        "Traceback (most recent call last):\n"
        '  File "/app/worker/config.py", line 12, in <module>\n'
        '    QUEUE_URL = os.environ["ESTOQUE_QUEUE_URL"]\n'
        "KeyError: 'ESTOQUE_QUEUE_URL'",
    ))
    e.logs.append(LogEfeito(
        "estoque-worker", "INFO",
        f"container estoque-worker reiniciado (restart #{k + 1}, motivo: Error, exit code 1)",
    ))
    if k > 4:
        e.logs.append(LogEfeito("pedidos-api", "WARN", f"fila estoque-reservas com {k * 120} mensagens acumuladas"))
    return e


def _recuperacao_worker(c: Cenario, m: datetime) -> Efeito:
    """Depois da correção o worker drena a fila acumulada."""
    e = Efeito()
    j = int((m - c.sintoma_fim) / MINUTO) + 1
    e.metricas[("estoque-worker", "requisicoes")] = 150.0
    e.metricas[("estoque-worker", "fila_mensagens")] = float(max(5, 5 + 120 * 20 - 600 * j))
    if j == 1:
        e.logs.append(LogEfeito("estoque-worker", "INFO", "ESTOQUE_QUEUE_URL configurada; estoque-worker consumindo a fila"))
    return e


def _certificado_expirado(c: Cenario, m: datetime, rng: Random) -> Efeito:
    e = Efeito()
    if not _ativo(c, m):
        return e
    for _ in range(rng.randint(10, 25)):
        e.logs.append(LogEfeito(
            "auth-api", "ERROR",
            "Erro ao buscar JWKS em https://idp.loja.internal/.well-known/jwks.json: "
            "SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] "
            "certificate verify failed: certificate has expired'))",
        ))
    e.metricas[("auth-api", "erros_5xx")] = float(rng.randint(40, 80))
    e.logs.append(LogEfeito("pedidos-api", "WARN", "auth-api retornou 500 ao validar token, requisição negada"))
    return e


def _vazamento_memoria(c: Cenario, m: datetime, rng: Random) -> Efeito:
    e = Efeito()
    deploy = _t(27, 11, 25)
    if m < deploy or m >= c.sintoma_fim:
        return e
    if m < c.sintoma_inicio:  # memória sobe desde o deploy
        mem = min(55 + 1.1 * (m - deploy) / MINUTO, 98)
        e.metricas[("auth-api", "memoria")] = _f(mem + rng.uniform(-0.5, 0.5))
        if mem >= 85:
            _gc(e, mem, rng)
        return e
    ciclo = _k(c, m) % 11
    if ciclo == 0:
        e.metricas[("auth-api", "memoria")] = 99.0
        e.metricas[("auth-api", "reinicios")] = 1.0
        e.metricas[("auth-api", "erros_5xx")] = float(rng.randint(30, 60))
        e.logs.append(LogEfeito("auth-api", "ERROR", "container auth-api terminado: OOMKilled (limite 512Mi)"))
        return e
    mem = min(60 + 3.5 * ciclo, 98)
    e.metricas[("auth-api", "memoria")] = _f(mem)
    if ciclo == 1:
        e.logs.append(LogEfeito("auth-api", "INFO", "container auth-api reiniciado (restart, motivo: OOMKilled)"))
    if ciclo > 7:
        _gc(e, mem, rng)
    return e


def _gc(e: Efeito, mem: float, rng: Random) -> None:
    e.metricas[("auth-api", "latencia_p95")] = float(rng.randint(900, 2000))
    e.logs.append(LogEfeito("auth-api", "WARN", f"GC overhead alto: 41% do tempo em coleta, heap usado {int(mem)}%"))


PAGAFACIL_URL = "https://api.pagafacil.com.br/v2/cobrancas"


def _gateway_fora(c: Cenario, m: datetime, rng: Random) -> Efeito:
    e = Efeito()
    fora_desde, volta = _t(29, 9, 5), c.sintoma_fim
    if fora_desde <= m < c.sintoma_inicio:  # primeiros sinais, ainda sem erro
        e.metricas[("pagamentos-api", "latencia_p95")] = float(rng.randint(800, 1500))
        e.logs.append(LogEfeito("pagamentos-api", "WARN", f"PagaFácil respondendo com lentidão em POST /v2/cobrancas ({rng.randint(2500, 2900)}ms)"))
        return e
    if m == volta:
        e.logs.append(LogEfeito("pagamentos-api", "INFO", f"chamadas ao PagaFácil normalizadas: POST {PAGAFACIL_URL} 200"))
    if volta <= m < volta + 5 * MINUTO:  # retentativas acumuladas
        e.metricas[("pagamentos-api", "requisicoes")] = _f(90 * rng.uniform(1.9, 2.5))
    if not _ativo(c, m):
        return e
    mensagens = [
        f"java.net.SocketTimeoutException: Read timed out ao chamar {PAGAFACIL_URL}",
        f"Falha ao chamar {PAGAFACIL_URL}: HTTP 503 Service Unavailable (tentativa 3/3)",
    ]
    for i in range(rng.randint(6, 14)):
        e.logs.append(LogEfeito("pagamentos-api", "ERROR", mensagens[i % 2]))
    e.logs.append(LogEfeito("pedidos-api", "WARN", "pagamentos-api respondeu 502 em POST /pagamentos"))
    e.metricas[("pagamentos-api", "erros_5xx")] = float(rng.randint(20, 35))
    e.metricas[("pagamentos-api", "latencia_p95")] = float(rng.randint(3000, 9000))
    return e


def _rate_limit(c: Cenario, m: datetime, rng: Random) -> Efeito:
    e = Efeito()
    if not _ativo(c, m):
        return e
    e.metricas[("pagamentos-api", "requisicoes")] = _f(rng.uniform(213, 237))
    e.metricas[("pagamentos-api", "erros_5xx")] = float(rng.randint(16, 28))
    for _ in range(rng.randint(4, 10)):
        e.logs.append(LogEfeito(
            "pagamentos-api", "WARN",
            "PagaFácil respondeu 429 Too Many Requests (X-RateLimit-Limit: 100/min, Retry-After: 30)",
        ))
    return e


CENARIOS: list[Cenario] = [
    Cenario("pool_esgotado", "Checkout lento e erros 500 no pedidos-api", "pedidos-api",
            _t(6, 13, 30), _t(6, 14, 30), _t(6, 14, 0), _t(6, 14, 30),
            "Pico de tráfego no pedidos-api esgotou o pool de conexões (máximo 10, reduzido pelo deploy v3.2.0).",
            _pool_esgotado),
    Cenario("banco_lento_com_deploy", "Lentidão e timeouts no pedidos-api e no estoque-worker", "pedidos-api",
            _t(8, 15, 15), _t(8, 16, 15), _t(8, 15, 47), _t(8, 16, 12),
            "Reindexação no db-principal travou a tabela estoque; o deploy v3.2.1 não é a causa.",
            _banco_lento,
            # Índice indisponível durante o REINDEX: quase tudo vira varredura sequencial.
            banco={"estoque": AnomaliaTabela(
                varreduras_sequenciais=(1800, 2600), varreduras_por_indice=(20, 90),
                inchaco_indice_pct=(40.0, 60.0), operacao_em_andamento="REINDEX TABLE estoque",
            )}),
    Cenario("deploy_com_bug", "Erros 500 ao confirmar pagamentos", "pagamentos-api",
            _t(14, 14, 15), _t(14, 15, 5), _t(14, 14, 38), _t(14, 15, 3),
            "O deploy v2.14.0 do pagamentos-api causa NullPointerException ao confirmar pagamento sem cupom.",
            _deploy_com_bug),
    Cenario("env_var_faltando", "Fila de reservas de estoque acumulando", "estoque-worker",
            _t(19, 16, 0), _t(19, 16, 45), _t(19, 16, 21), _t(19, 16, 41),
            "O deploy v1.6.0 do estoque-worker exige ESTOQUE_QUEUE_URL, não configurada no ambiente.",
            _env_var_faltando),
    Cenario("certificado_expirado", "auth-api recusando validação de tokens", "auth-api",
            _t(23, 20, 30), _t(23, 21, 30), _t(23, 21, 0), _t(23, 21, 30),
            "O certificado TLS do idp.loja.internal expirou e o auth-api não valida tokens.",
            _certificado_expirado),
    Cenario("vazamento_memoria", "auth-api reiniciando e com latência alta", "auth-api",
            _t(27, 11, 15), _t(27, 12, 55), _t(27, 12, 5), _t(27, 12, 53),
            "O deploy v1.8.0 do auth-api introduziu cache sem limite que vaza memória até OOMKilled.",
            _vazamento_memoria),
    Cenario("gateway_fora", "Erros 502 e timeouts nas cobranças", "pagamentos-api",
            _t(29, 8, 50), _t(29, 10, 40), _t(29, 9, 10), _t(29, 10, 20),
            "O gateway externo PagaFácil ficou indisponível (HTTP 503). Nenhuma mudança no código.",
            _gateway_fora),
    Cenario("rate_limit", "Cobranças recusadas em pico de tráfego", "pagamentos-api",
            _t(30, 19, 45), _t(30, 20, 30), _t(30, 20, 5), _t(30, 20, 25),
            "O tráfego estourou o limite de 100 requisições por minuto do PagaFácil (HTTP 429).",
            _rate_limit),
]


def cenario_em(m: datetime) -> Cenario | None:
    """Cenário cuja janela contém o minuto `m` (as janelas não se sobrepõem)."""
    return next((c for c in CENARIOS if c.janela_inicio <= m < c.janela_fim), None)
