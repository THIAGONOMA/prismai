"""Integration tests for living review pipeline."""
from __future__ import annotations

import pytest

from prismai.checks.impact import detectar_impacto
from prismai.persistence.memory import InMemoryRepository


class TestLivingPipeline:
    @pytest.mark.asyncio
    async def test_enable_and_update(self):
        repo = InMemoryRepository()
        await repo.create_review("rev1")
        await repo.set_protocol("rev1", {
            "pergunta": "test?", "P": "p", "I": "i", "C": "c", "O": "o",
            "inclusao": ["a"], "exclusao": ["b"],
        })

        await repo.enable_living("rev1", "0 3 * * 1")

        living = await repo.get_living_reviews()
        assert len(living) == 1
        assert living[0]["id"] == "rev1"

        await repo.add_living_update("rev1", {
            "trigger": "scheduled",
            "search_sources": ["openalex"],
            "new_found": 100, "new_imported": 3, "new_duplicates": 97,
            "screening_status": "completed",
            "impact_status": "completed",
            "impact_result": {
                "impacto": True,
                "detalhes": [{"outcome_key": "pain", "tipo": "mudanca_direcao", "descricao": "test"}],
            },
            "notified": False,
        })

        updates = await repo.get_living_updates("rev1")
        assert len(updates) == 1
        assert updates[0]["impact_result"]["impacto"] is True

    @pytest.mark.asyncio
    async def test_impact_detection_integration(self):
        syntheses_antes = [
            {"outcome_key": "pain", "pooled_effect": 0.5, "p_value": 0.01, "i2": 25.0},
            {"outcome_key": "mobility", "pooled_effect": 0.3, "p_value": 0.04, "i2": 40.0},
        ]
        syntheses_depois = [
            {"outcome_key": "pain", "pooled_effect": -0.2, "p_value": 0.15, "i2": 55.0},
            {"outcome_key": "mobility", "pooled_effect": 0.35, "p_value": 0.03, "i2": 42.0},
        ]

        result = detectar_impacto(syntheses_antes, syntheses_depois)
        assert result.impacto
        pain_impacts = [d for d in result.detalhes if d.outcome_key == "pain"]
        assert len(pain_impacts) >= 2
        mobility_impacts = [d for d in result.detalhes if d.outcome_key == "mobility"]
        assert len(mobility_impacts) == 0

    @pytest.mark.asyncio
    async def test_no_living_updates_initially(self):
        repo = InMemoryRepository()
        await repo.create_review("rev2")
        updates = await repo.get_living_updates("rev2")
        assert len(updates) == 0
        living = await repo.get_living_reviews()
        assert len(living) == 0
