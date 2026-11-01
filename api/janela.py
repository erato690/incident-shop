"""Resolução da janela de tempo das consultas (cenario, inicio, fim)."""

from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=-3))
JANELA_MAXIMA = timedelta(hours=6)


class ErroJanela(ValueError):
    """Janela inválida; `campo` indica o parâmetro responsável."""

    def __init__(self, campo: str, mensagem: str):
        super().__init__(mensagem)
        self.campo = campo


def normalizar(horario: datetime | None) -> datetime | None:
    """Sem fuso vale -03:00; com fuso converte para -03:00; descarta microssegundos."""
    if horario is None:
        return None
    if horario.tzinfo is None:
        horario = horario.replace(tzinfo=TZ)
    return horario.astimezone(TZ).replace(microsecond=0)


def resolver_janela(
    do_cenario: tuple[datetime, datetime] | None,
    inicio: datetime | None,
    fim: datetime | None,
    exigir: bool,
) -> tuple[datetime | None, datetime | None]:
    """Combina cenário e horários explícitos (o explícito vale) e valida a janela."""
    inicio, fim = normalizar(inicio), normalizar(fim)
    if do_cenario is not None:
        inicio = inicio or do_cenario[0]
        fim = fim or do_cenario[1]
    if inicio is None or fim is None:
        if exigir:
            raise ErroJanela("inicio", "informe 'cenario' ou 'inicio' e 'fim'")
        return inicio, fim
    if inicio >= fim:
        raise ErroJanela("inicio", "'inicio' deve ser menor que 'fim'")
    if fim - inicio > JANELA_MAXIMA:
        raise ErroJanela("fim", "a janela pode ter no máximo 6 horas")
    return inicio, fim
