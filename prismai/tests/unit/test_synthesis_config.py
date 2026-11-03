"""Tests for prismai.core.synthesis_config."""
from __future__ import annotations

import pytest

from prismai.core.synthesis_config import carregar_synthesis_config


class TestCarregarSynthesisConfig:
    def test_valid(self):
        raw = {
            "version": "v1",
            "outcomes": [
                {"key": "pain", "nome": "Dor", "tipo": "continuous", "measure": "smd"},
            ],
        }
        cfg = carregar_synthesis_config(raw)
        assert cfg is not None
        assert len(cfg.outcomes) == 1
        assert cfg.outcomes[0].key == "pain"

    def test_none_returns_none(self):
        assert carregar_synthesis_config(None) is None

    def test_invalid_raises(self):
        with pytest.raises(Exception):
            carregar_synthesis_config({"version": "v1", "outcomes": [{"invalid": True}]})
