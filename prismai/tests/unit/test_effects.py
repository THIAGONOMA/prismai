"""Tests for prismai.synthesis.effects — study-level effect size computation."""
from __future__ import annotations

import math

from prismai.synthesis.effects import efeito_estudo


class TestSMD:
    def test_hedges_g_basic(self):
        cells = {
            "n_intervencao": 30, "n_controle": 30,
            "media_intervencao": 5.0, "dp_intervencao": 2.0,
            "media_controle": 3.0, "dp_controle": 2.0,
        }
        r = efeito_estudo(cells, "smd")
        assert "erro" not in r
        assert abs(r["yi"] - 0.98) < 0.05  # Hedges g ~= d * J
        assert r["vi"] > 0
        assert r["n_total"] == 60

    def test_smd_zero_sd_raises(self):
        cells = {
            "n_intervencao": 10, "n_controle": 10,
            "media_intervencao": 5.0, "dp_intervencao": 0.0,
            "media_controle": 3.0, "dp_controle": 0.0,
        }
        r = efeito_estudo(cells, "smd")
        assert "erro" in r

    def test_smd_missing_field(self):
        r = efeito_estudo({"n_intervencao": 30}, "smd")
        assert "erro" in r


class TestMD:
    def test_md_basic(self):
        cells = {
            "n_intervencao": 50, "n_controle": 50,
            "media_intervencao": 10.0, "dp_intervencao": 3.0,
            "media_controle": 8.0, "dp_controle": 3.0,
        }
        r = efeito_estudo(cells, "md")
        assert "erro" not in r
        assert abs(r["yi"] - 2.0) < 1e-6
        assert r["n_total"] == 100

    def test_md_negative(self):
        cells = {
            "n_intervencao": 50, "n_controle": 50,
            "media_intervencao": 8.0, "dp_intervencao": 3.0,
            "media_controle": 10.0, "dp_controle": 3.0,
        }
        r = efeito_estudo(cells, "md")
        assert r["yi"] < 0


class TestRR:
    def test_rr_basic(self):
        cells = {
            "eventos_intervencao": 10, "n_intervencao": 100,
            "eventos_controle": 20, "n_controle": 100,
        }
        r = efeito_estudo(cells, "rr")
        assert "erro" not in r
        assert abs(r["yi"] - math.log(0.5)) < 0.01

    def test_rr_zero_cell(self):
        cells = {
            "eventos_intervencao": 0, "n_intervencao": 50,
            "eventos_controle": 10, "n_controle": 50,
        }
        r = efeito_estudo(cells, "rr")
        assert "erro" not in r
        assert r["yi"] < 0  # continuity correction applied


class TestOR:
    def test_or_basic(self):
        cells = {
            "eventos_intervencao": 10, "n_intervencao": 100,
            "eventos_controle": 20, "n_controle": 100,
        }
        r = efeito_estudo(cells, "or")
        assert "erro" not in r
        expected_or = (10 * 80) / (90 * 20)
        assert abs(r["yi"] - math.log(expected_or)) < 0.01

    def test_or_zero_cell_correction(self):
        cells = {
            "eventos_intervencao": 0, "n_intervencao": 50,
            "eventos_controle": 10, "n_controle": 50,
        }
        r = efeito_estudo(cells, "or")
        assert "erro" not in r


class TestUnknownMeasure:
    def test_unknown(self):
        r = efeito_estudo({}, "unknown")
        assert "erro" in r
