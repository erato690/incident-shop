"""Os 9 deploys reais do repositório (tag, commit, autor e assunto vêm do git)."""

from datetime import datetime

from api.janela import TZ
from api.modelos import Deploy


def _d(dia: int, hora: int, minuto: int, tag: str, commit: str, autor: str, mensagem: str) -> Deploy:
    servico, versao = tag.split("/v")
    return Deploy(
        horario=datetime(2026, 10, dia, hora, minuto, tzinfo=TZ), servico=servico, versao=versao,
        tag=tag, commit=commit, autor=autor, mensagem=mensagem,
    )

DEPLOYS: list[Deploy] = [
    _d(1, 10, 0, "pedidos-api/v3.1.0", "7a0ac2d", "Equipe Loja",
       "chore(pedidos-api): estado inicial saudável"),
    _d(6, 13, 40, "pedidos-api/v3.2.0", "a356b1f", "Equipe Loja",
       "perf: reduz pool máximo de 20 para 10 para aliviar o db-principal"),
    _d(8, 15, 45, "pedidos-api/v3.2.1", "60b41c3", "joao.pereira",
       "fix: corrige texto do e-mail de confirmação (e90a4d7)"),
    _d(12, 10, 0, "pagamentos-api/v2.13.4", "93bfa78", "Equipe Loja",
       "chore(pagamentos-api): estado inicial saudável"),
    _d(14, 14, 35, "pagamentos-api/v2.14.0", "6245f86", "ana.souza",
       "feat: aplica desconto de cupom na confirmação do pagamento (a1f3c9e)"),
    _d(16, 10, 0, "estoque-worker/v1.5.2", "d63ba40", "Equipe Loja",
       "chore(estoque-worker): estado inicial saudável"),
    _d(19, 16, 20, "estoque-worker/v1.6.0", "d5c8f27", "carlos.lima",
       "refactor: lê a URL da fila da variável de ambiente ESTOQUE_QUEUE_URL (7bd0e21)"),
    _d(22, 10, 0, "auth-api/v1.7.9", "651362e", "Equipe Loja",
       "chore(auth-api): estado inicial saudável"),
    _d(27, 11, 25, "auth-api/v1.8.0", "7694861", "beatriz.alves",
       "feat: adiciona cache em memória sem limite para tokens validados (c44e8b0)"),
]

# Mensagem do log INFO emitido quando o deploy termina (padrão: genérica).
LOG_DEPLOY: dict[str, str] = {
    "pedidos-api/v3.2.0": "pedidos-api 3.2.0 iniciado (deploy, commit a356b1f): pool_max=10",
}


def mensagem_log_deploy(d: Deploy) -> str:
    return LOG_DEPLOY.get(d.tag, f"{d.servico} {d.versao} iniciado (deploy, commit {d.commit})")
