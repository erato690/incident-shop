"""Esqueleto da fonte de serviços reais (opção 2): os dados vêm dos contêineres, não da simulação.

Nada aqui está implementado. Cada método explica de onde o dado viria; o desenho completo está
em docs/opcao2-servicos-reais.md. As rotas não mudam: só esta classe substitui `FonteSimulada`.
"""

from datetime import datetime

from api.modelos import (
    CenarioPublico,
    Deploy,
    Metrica,
    Nivel,
    RegistroLog,
    SerieMetrica,
    Servico,
    TabelaBanco,
)

MENSAGEM = "FONTE_DADOS=servicos ainda não existe; veja docs/opcao2-servicos-reais.md"


class FonteServicos:
    """Implementação futura de `FonteDados` sobre os quatro serviços reais rodando em contêineres."""

    nome = "servicos"

    def verificar(self) -> None:
        """Falha cedo, na criação da fonte, enquanto a opção 2 não estiver implementada."""
        raise NotImplementedError(MENSAGEM)

    def cenarios(self) -> list[CenarioPublico]:
        """Catálogo de injeção: cada cenário é uma falha que a rota `POST /injecoes` (fora do
        contrato 1.0) sabe provocar; o catálogo guarda id, título, serviço, início do sintoma e
        a janela observada, sem expor a causa raiz."""
        raise NotImplementedError(MENSAGEM)

    def logs(
        self, servico: Servico | None, nivel: Nivel | None, inicio: datetime, fim: datetime
    ) -> list[RegistroLog]:
        """Logs coletados dos contêineres: um agregador no estilo Loki (consulta por rótulo e
        intervalo) ou o arquivo JSON de log que o Docker grava por contêiner, lido e filtrado
        por serviço, nível e janela, em ordem crescente de horário."""
        raise NotImplementedError(MENSAGEM)

    def metricas(
        self, servico: Servico | None, metrica: Metrica | None, inicio: datetime, fim: datetime
    ) -> list[SerieMetrica]:
        """Métricas do Prometheus (consulta de intervalo com passo de 60 s), convertidas para um
        ponto por minuto na unidade do contrato, com o resumo (min, max, média, último) calculado
        sobre os pontos."""
        raise NotImplementedError(MENSAGEM)

    def deploys(
        self, servico: Servico | None, inicio: datetime | None, fim: datetime | None
    ) -> list[Deploy]:
        """Deploys das tags git do repositório (tag, commit, autor e mensagem) cruzadas com o
        registro de deploy do ambiente, que dá o horário em que a versão entrou em produção."""
        raise NotImplementedError(MENSAGEM)

    def estatisticas_banco(self, cenario: str, servico: Servico | None) -> list[TabelaBanco]:
        """Retrato do db-principal no início do sintoma do cenário, lido do PostgreSQL:
        `pg_stat_user_tables` (varreduras sequenciais e por índice), `pg_stat_progress_create_index`
        e `pg_stat_activity` (REINDEX em andamento e a instrução em execução) e a coluna
        `last_analyze`; o inchaço do índice vem de uma estimativa sobre o tamanho do índice."""
        raise NotImplementedError(MENSAGEM)
