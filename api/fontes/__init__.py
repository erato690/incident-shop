"""Interface da fonte de dados e fábrica escolhida por FONTE_DADOS."""

import os
from datetime import datetime
from typing import Protocol

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


class FonteDados(Protocol):
    """Contrato entre as rotas e quem produz os dados (simulada hoje, serviços reais na opção 2)."""

    nome: str

    def cenarios(self) -> list[CenarioPublico]: ...

    def logs(
        self, servico: Servico | None, nivel: Nivel | None, inicio: datetime, fim: datetime
    ) -> list[RegistroLog]: ...

    def metricas(
        self, servico: Servico | None, metrica: Metrica | None, inicio: datetime, fim: datetime
    ) -> list[SerieMetrica]: ...

    def deploys(
        self, servico: Servico | None, inicio: datetime | None, fim: datetime | None
    ) -> list[Deploy]: ...

    def estatisticas_banco(self, cenario: str, servico: Servico | None) -> list[TabelaBanco]: ...


def criar_fonte() -> FonteDados:
    """Cria a fonte indicada em FONTE_DADOS (padrão: simulada)."""
    nome = os.environ.get("FONTE_DADOS", "simulada")
    if nome == "simulada":
        from api.fontes.simulada import FonteSimulada

        return FonteSimulada()
    if nome == "servicos":
        from api.fontes.servicos import FonteServicos

        fonte = FonteServicos()
        fonte.verificar()
        return fonte
    raise ValueError(f"FONTE_DADOS inválida: '{nome}'. Use 'simulada' ou 'servicos'.")
