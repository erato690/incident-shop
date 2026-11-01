from datetime import datetime, timedelta, timezone

import pytest

from api.janela import TZ, ErroJanela, resolver_janela

T0 = datetime(2026, 10, 6, 13, 30, tzinfo=TZ)
T1 = datetime(2026, 10, 6, 14, 30, tzinfo=TZ)


def test_fuso_e_menos_tres():
    assert TZ.utcoffset(None) == timedelta(hours=-3)


def test_cenario_preenche_janela():
    assert resolver_janela((T0, T1), None, None, True) == (T0, T1)


def test_janela_explicita_vale_sobre_cenario():
    i = datetime(2026, 10, 6, 14, 0, tzinfo=TZ)
    assert resolver_janela((T0, T1), i, None, True) == (i, T1)


def test_entrada_sem_fuso_vale_menos_tres():
    i, f = resolver_janela(None, datetime(2026, 10, 6, 14, 0), datetime(2026, 10, 6, 15, 0), True)
    assert i.utcoffset() == timedelta(hours=-3) and i.hour == 14 and f.hour == 15


def test_outro_fuso_e_convertido():
    utc = timezone.utc
    i, _ = resolver_janela(None, datetime(2026, 10, 6, 17, 0, tzinfo=utc), datetime(2026, 10, 6, 18, 0, tzinfo=utc), True)
    assert (i.hour, i.utcoffset()) == (14, timedelta(hours=-3))


def test_exige_janela():
    with pytest.raises(ErroJanela):
        resolver_janela(None, None, None, True)
    with pytest.raises(ErroJanela):
        resolver_janela(None, T0, None, True)


def test_sem_exigir_aceita_vazio():
    assert resolver_janela(None, None, None, False) == (None, None)


def test_inicio_menor_que_fim():
    with pytest.raises(ErroJanela):
        resolver_janela(None, T1, T0, True)
    with pytest.raises(ErroJanela):
        resolver_janela(None, T0, T0, True)


def test_maximo_seis_horas():
    assert resolver_janela(None, T0, T0 + timedelta(hours=6), True)[1] == T0 + timedelta(hours=6)
    with pytest.raises(ErroJanela):
        resolver_janela(None, T0, T0 + timedelta(hours=6, seconds=1), True)


def test_microssegundos_descartados():
    i, _ = resolver_janela(None, T0.replace(microsecond=5), T1, True)
    assert i.microsecond == 0
