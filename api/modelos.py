"""Modelos Pydantic de resposta: o contrato da API (OpenAPI) nasce daqui."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Servico = Literal["pedidos-api", "pagamentos-api", "estoque-worker", "auth-api"]
Nivel = Literal["INFO", "WARN", "ERROR"]
Metrica = Literal[
    "requisicoes", "erros_5xx", "latencia_p95", "cpu", "memoria",
    "reinicios", "conexoes_db", "fila_mensagens",
]


class RespostaSaude(BaseModel):
    status: Literal["ok"]
    fonte: str
    versao_contrato: str


class Janela(BaseModel):
    inicio: datetime
    fim: datetime


class CenarioPublico(BaseModel):
    id: str
    titulo: str
    servico: Servico
    sintoma_inicio: datetime
    janela: Janela


class RespostaCenarios(BaseModel):
    cenarios: list[CenarioPublico]


class RegistroLog(BaseModel):
    horario: datetime
    servico: Servico
    nivel: Nivel
    mensagem: str


class ConsultaLogs(BaseModel):
    cenario: str | None
    servico: Servico | None
    nivel: Nivel | None
    inicio: datetime
    fim: datetime


class RespostaLogs(BaseModel):
    consulta: ConsultaLogs
    total: int
    truncado: bool
    logs: list[RegistroLog]


class Ponto(BaseModel):
    horario: datetime
    valor: float


class Resumo(BaseModel):
    min: float
    max: float
    media: float
    ultimo: float


class SerieMetrica(BaseModel):
    servico: Servico
    metrica: Metrica
    unidade: str
    resumo: Resumo
    pontos: list[Ponto]


class ConsultaMetricas(BaseModel):
    cenario: str | None
    servico: Servico | None
    metrica: Metrica | None
    inicio: datetime
    fim: datetime


class RespostaMetricas(BaseModel):
    consulta: ConsultaMetricas
    series: list[SerieMetrica]


class Deploy(BaseModel):
    horario: datetime
    servico: Servico
    versao: str
    tag: str
    commit: str
    autor: str
    mensagem: str


class ConsultaDeploys(BaseModel):
    cenario: str | None
    servico: Servico | None
    inicio: datetime | None
    fim: datetime | None


class RespostaDeploys(BaseModel):
    consulta: ConsultaDeploys
    deploys: list[Deploy]


class ConsultaEstatisticasBanco(BaseModel):
    cenario: str
    servico: Servico | None
    momento: datetime


class TabelaBanco(BaseModel):
    tabela: str
    servicos: list[Servico]
    varreduras_sequenciais: int
    varreduras_por_indice: int
    reindexacao_em_andamento: bool
    operacao_em_andamento: str | None
    ultimo_analyze: datetime
    inchaco_indice_pct: float


class RespostaEstatisticasBanco(BaseModel):
    consulta: ConsultaEstatisticasBanco
    banco: str
    tabelas: list[TabelaBanco]
