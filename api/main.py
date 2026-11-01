"""API HTTP só de leitura com logs, métricas e deploys da loja fictícia (contrato 1.0.0)."""

from datetime import datetime
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query

from api.fontes import FonteDados, criar_fonte
from api.janela import ErroJanela, resolver_janela
from api.modelos import (
    CenarioPublico, ConsultaDeploys, ConsultaLogs, ConsultaMetricas, Metrica, Nivel, RespostaCenarios,
    RespostaDeploys, RespostaLogs, RespostaMetricas, RespostaSaude, Servico,
)

VERSAO_CONTRATO = "1.0.0"

DESCRICAO = (
    "API só de leitura com logs, métricas e deploys da loja fictícia, consumida pelo incident-agent. "
    "Horários em ISO 8601 com fuso -03:00; a mesma requisição devolve sempre o mesmo corpo."
)
NAO_ENCONTRADO = {404: {"description": "O `cenario` informado não existe."}}

app = FastAPI(title="incident-shop", version=VERSAO_CONTRATO, description=DESCRICAO)


@lru_cache(maxsize=1)
def _fonte_padrao() -> FonteDados:
    return criar_fonte()


def obter_fonte() -> FonteDados:
    """Dependência das rotas; os testes a trocam com `app.dependency_overrides`."""
    return _fonte_padrao()


Fonte = Annotated[FonteDados, Depends(obter_fonte)]
CenarioQ = Annotated[str | None, Query(description="Id de um cenário de GET /cenarios.")]
ServicoQ = Annotated[Servico | None, Query(description="Filtra por serviço.")]
InicioQ = Annotated[datetime | None, Query(description="Começo da janela (inclusivo); sem fuso vale -03:00.")]
FimQ = Annotated[datetime | None, Query(description="Fim da janela (exclusivo); sem fuso vale -03:00.")]


def _janela(fonte: FonteDados, cenario: str | None, inicio, fim, exigir: bool):
    do_cenario = None
    if cenario is not None:
        achado = next((c for c in fonte.cenarios() if c.id == cenario), None)
        if achado is None:
            raise HTTPException(status_code=404, detail=f"cenário '{cenario}' não existe")
        do_cenario = (achado.janela.inicio, achado.janela.fim)
    try:
        return resolver_janela(do_cenario, inicio, fim, exigir)
    except ErroJanela as erro:
        detalhe = [{"loc": ["query", erro.campo], "msg": str(erro), "type": "value_error"}]
        raise HTTPException(status_code=422, detail=detalhe) from erro


@app.get("/saude", response_model=RespostaSaude, summary="Verifica se a API está no ar")
def saude(fonte: Fonte) -> RespostaSaude:
    """Devolve o estado da API, o nome da fonte de dados ativa e a versão do contrato."""
    return RespostaSaude(status="ok", fonte=fonte.nome, versao_contrato=VERSAO_CONTRATO)


@app.get("/cenarios", response_model=RespostaCenarios, summary="Lista os cenários e suas janelas")
def cenarios(fonte: Fonte) -> RespostaCenarios:
    """Lista os 8 cenários de incidente com a janela de tempo de cada um. Não expõe a causa raiz."""
    return RespostaCenarios(cenarios=fonte.cenarios())


@app.get("/logs", response_model=RespostaLogs, summary="Consulta logs por janela", responses=NAO_ENCONTRADO)
def logs(
    fonte: Fonte, cenario: CenarioQ = None, servico: ServicoQ = None, inicio: InicioQ = None,
    fim: FimQ = None, nivel: Annotated[Nivel | None, Query(description="Filtro exato de nível.")] = None,
    limite: Annotated[int, Query(ge=1, le=5000, description="Máximo de logs devolvidos.")] = 500,
) -> RespostaLogs:
    """Logs em ordem crescente de horário. Exige janela (`cenario` ou `inicio` e `fim`, até 6 horas).
    `total` conta todos os logs dos filtros; `truncado` indica que `total` passa de `limite`."""
    ini, fi = _janela(fonte, cenario, inicio, fim, exigir=True)
    todos = fonte.logs(servico, nivel, ini, fi)
    consulta = ConsultaLogs(cenario=cenario, servico=servico, nivel=nivel, inicio=ini, fim=fi)
    return RespostaLogs(consulta=consulta, total=len(todos), truncado=len(todos) > limite, logs=todos[:limite])


@app.get(
    "/metricas", response_model=RespostaMetricas, summary="Consulta métricas por janela",
    responses=NAO_ENCONTRADO,
)
def metricas(
    fonte: Fonte, cenario: CenarioQ = None, servico: ServicoQ = None, inicio: InicioQ = None,
    fim: FimQ = None, metrica: Annotated[Metrica | None, Query(description="Nome da métrica.")] = None,
) -> RespostaMetricas:
    """Uma série por serviço e métrica, com um ponto por minuto da janela e um resumo.
    Exige janela (`cenario` ou `inicio` e `fim`, até 6 horas)."""
    ini, fi = _janela(fonte, cenario, inicio, fim, exigir=True)
    consulta = ConsultaMetricas(cenario=cenario, servico=servico, metrica=metrica, inicio=ini, fim=fi)
    return RespostaMetricas(consulta=consulta, series=fonte.metricas(servico, metrica, ini, fi))


@app.get("/deploys", response_model=RespostaDeploys, summary="Consulta deploys", responses=NAO_ENCONTRADO)
def deploys(
    fonte: Fonte, cenario: CenarioQ = None, servico: ServicoQ = None, inicio: InicioQ = None, fim: FimQ = None,
) -> RespostaDeploys:
    """Deploys reais do repositório em ordem crescente de horário. Sem janela, devolve todo o histórico;
    com só `inicio` ou só `fim`, o outro lado fica aberto."""
    ini, fi = _janela(fonte, cenario, inicio, fim, exigir=False)
    consulta = ConsultaDeploys(cenario=cenario, servico=servico, inicio=ini, fim=fi)
    return RespostaDeploys(consulta=consulta, deploys=fonte.deploys(servico, ini, fi))
