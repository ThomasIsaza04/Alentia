"""Pruebas unitarias de las reglas de perfiles (no requieren base de datos)."""
from datetime import date

from app.services.perfiles import es_menor


def test_menor_de_18_anos() -> None:
    assert es_menor(date(2015, 6, 1), date(2026, 10, 13))


def test_el_dia_del_cumpleanos_de_los_18_ya_no_es_menor() -> None:
    assert not es_menor(date(2008, 10, 13), date(2026, 10, 13))


def test_un_dia_antes_del_cumpleanos_de_los_18_sigue_siendo_menor() -> None:
    assert es_menor(date(2008, 10, 14), date(2026, 10, 13))


def test_adulto_mayor_no_es_menor() -> None:
    assert not es_menor(date(1940, 1, 1), date(2026, 10, 13))
