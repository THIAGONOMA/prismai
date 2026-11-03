from prismai.core.models import CasoTeste, Protocolo, Registro
from prismai.eval.golden import (
    carregar_casos,
    carregar_pares,
    carregar_protocolo,
    carregar_registros,
)


class TestCarregarProtocolo:
    def test_returns_protocolo_with_pergunta(self):
        p = carregar_protocolo()
        assert isinstance(p, Protocolo)
        assert "LLM" in p.pergunta


class TestCarregarRegistros:
    def test_returns_13_registros(self):
        regs = carregar_registros()
        assert len(regs) == 13
        assert all(isinstance(r, Registro) for r in regs)


class TestCarregarCasos:
    def test_returns_13_casos(self):
        casos = carregar_casos()
        assert len(casos) == 13
        assert all(isinstance(c, CasoTeste) for c in casos)


class TestCarregarPares:
    def test_has_expected_keys(self):
        pares = carregar_pares()
        assert "Par1_pais" in pares
        assert "Par2_registro" in pares
