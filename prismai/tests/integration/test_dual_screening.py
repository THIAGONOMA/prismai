"""Integration test: dual screening with fake LLMs producing divergent decisions."""
from __future__ import annotations

import pytest

from prismai.api.deps import get_repo, reset_repo


@pytest.fixture(autouse=True)
def _clean_repo():
    reset_repo()
    yield
    reset_repo()


PROTOCOL = {
    "pergunta": "LLM em educação?",
    "P": "estudantes",
    "I": "chatbot LLM",
    "C": "sem chatbot",
    "O": "desempenho",
    "desenho": "RCT",
    "inclusao": ["usa LLM"],
    "exclusao": ["opinião"],
}

REGISTRO = {
    "id": "r1",
    "titulo": "LLM Tutoring Study",
    "abstract": "This study evaluated the impact of a GPT-based tutoring chatbot on academic performance.",
}


class _FakeLLM:
    """Minimal fake that returns a fixed decision string when invoked."""

    def __init__(self, decision: str):
        self._decision = decision

    def invoke(self, messages, **kwargs):
        import json

        from langchain_core.messages import AIMessage

        resp = json.dumps({
            "decision": self._decision,
            "reasons": ["fake reason"],
            "evidence": ["fake evidence"],
            "confidence": "high",
        })
        return AIMessage(content=resp)


class TestDualScreening:
    @pytest.mark.asyncio
    async def test_divergent_decisions_create_conflict(self):
        from prismai.graphs.dual_screening import screen_dual

        llm_a = _FakeLLM("include")
        llm_b = _FakeLLM("exclude")

        resp_a, _, resp_b, _, conflict = await screen_dual(
            REGISTRO, PROTOCOL, llm_a, llm_b,
        )

        assert resp_a.resultado.decision == "include"
        assert resp_b.resultado.decision == "exclude"
        assert conflict is not None
        assert conflict["disagreement_score"] == 3.0
        assert conflict["status"] == "pending"

    @pytest.mark.asyncio
    async def test_agreeing_decisions_no_conflict(self):
        from prismai.graphs.dual_screening import screen_dual

        llm_a = _FakeLLM("include")
        llm_b = _FakeLLM("include")

        resp_a, _, resp_b, _, conflict = await screen_dual(
            REGISTRO, PROTOCOL, llm_a, llm_b,
        )

        assert resp_a.resultado.decision == "include"
        assert resp_b.resultado.decision == "include"
        assert conflict is None

    @pytest.mark.asyncio
    async def test_conflict_persisted_in_repo(self):
        from prismai.graphs.dual_screening import screen_dual

        repo = get_repo()
        await repo.create_review("rev1")

        llm_a = _FakeLLM("include")
        llm_b = _FakeLLM("exclude")

        _, _, _, _, conflict = await screen_dual(
            REGISTRO, PROTOCOL, llm_a, llm_b,
        )
        assert conflict is not None

        await repo.add_conflict("rev1", conflict)
        conflicts = await repo.get_conflicts("rev1", status="pending")
        assert len(conflicts) == 1
        assert conflicts[0]["disagreement_score"] == 3.0
