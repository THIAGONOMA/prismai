"""Unit tests for numeric consistency checks."""
from __future__ import annotations

from prismai.checks.numeric import verificar_consistencia


def test_clean_data_no_flags():
    cells = [
        {"field": "n_intervencao", "value": 50},
        {"field": "n_controle", "value": 50},
        {"field": "n_total", "value": 100},
        {"field": "dp_intervencao", "value": 2.5},
        {"field": "dp_controle", "value": 3.0},
        {"field": "valor_p", "value": 0.05},
        {"field": "ano_publicacao", "value": 2023},
    ]
    flags = verificar_consistencia(cells)
    assert flags == []


def test_n_total_mismatch():
    cells = [
        {"field": "n_intervencao", "value": 50},
        {"field": "n_controle", "value": 40},
        {"field": "n_total", "value": 100},
    ]
    flags = verificar_consistencia(cells)
    assert len(flags) == 1
    assert "n_total" in flags[0]


def test_negative_sd():
    cells = [
        {"field": "dp_intervencao", "value": -1.5},
    ]
    flags = verificar_consistencia(cells)
    assert len(flags) == 1
    assert "positivo" in flags[0]


def test_zero_sd():
    cells = [
        {"field": "dp_controle", "value": 0},
    ]
    flags = verificar_consistencia(cells)
    assert len(flags) == 1
    assert "positivo" in flags[0]


def test_valor_p_out_of_range():
    cells = [
        {"field": "valor_p", "value": 1.5},
    ]
    flags = verificar_consistencia(cells)
    assert len(flags) == 1
    assert "valor_p" in flags[0]


def test_valor_p_negative():
    cells = [
        {"field": "valor_p", "value": -0.1},
    ]
    flags = verificar_consistencia(cells)
    assert len(flags) == 1


def test_year_too_old():
    cells = [
        {"field": "ano_publicacao", "value": 1800},
    ]
    flags = verificar_consistencia(cells)
    assert len(flags) == 1
    assert "plausível" in flags[0]


def test_year_future():
    cells = [
        {"field": "ano_publicacao", "value": 3000},
    ]
    flags = verificar_consistencia(cells)
    assert len(flags) == 1


def test_valid_year_boundary():
    cells = [
        {"field": "ano_publicacao", "value": 1900},
    ]
    flags = verificar_consistencia(cells)
    assert flags == []


def test_missing_fields_no_crash():
    cells = [
        {"field": "media_intervencao", "value": 5.0},
    ]
    flags = verificar_consistencia(cells)
    assert flags == []


def test_none_values_handled():
    cells = [
        {"field": "n_total", "value": None},
        {"field": "dp_intervencao", "value": None},
    ]
    flags = verificar_consistencia(cells)
    assert flags == []


def test_multiple_flags():
    cells = [
        {"field": "n_intervencao", "value": 30},
        {"field": "n_controle", "value": 30},
        {"field": "n_total", "value": 100},
        {"field": "dp_intervencao", "value": -1},
        {"field": "valor_p", "value": 2.0},
    ]
    flags = verificar_consistencia(cells)
    assert len(flags) == 3
