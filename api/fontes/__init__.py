"""Interface da fonte de dados e fábrica escolhida por FONTE_DADOS."""

import os
from datetime import datetime
from typing import Protocol

from api.modelos import CenarioPublico, Deploy, Metrica, Nivel, RegistroLog, SerieMetrica, Servico


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


def criar_fonte() -> FonteDados:
    """Cria a fonte indicada em FONTE_DADOS (padrão: simulada)."""
    nome = os.environ.get("FONTE_DADOS", "simulada")
    if nome == "simulada":
        from api.fontes.simulada import FonteSimulada

        return FonteSimulada()
    if nome == "servicos":
        raise NotImplementedError(
            "FONTE_DADOS=servicos ainda não existe; veja docs/opcao2-servicos-reais.md"
        )
    raise ValueError(f"FONTE_DADOS inválida: '{nome}'. Use 'simulada' ou 'servicos'.")
