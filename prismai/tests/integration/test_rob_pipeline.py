"""Integration test for the RoB graph with a fake LLM."""
from __future__ import annotations

import json

from prismai.core.models import RobResult
from prismai.graphs.rob import assess_rob


class FakeRobLLM:
    """Returns all-Y answers for every domain."""

    def invoke(self, prompt: str):
        import re

        questions = re.findall(r"- (\d+\.\d+):", prompt)
        data = [
            {
                "question_id": q,
                "answer": "Y",
                "reasoning": "Evidence supports favorable assessment.",
                "evidence_text": "randomized controlled trial with adequate blinding",
            }
            for q in questions
        ]

        class Resp:
            pass

        r = Resp()
        r.content = json.dumps(data)
        return r


_DOC = {
    "record_id": "rec-rob-1",
    "content_text": (
        "This was a randomized controlled trial with adequate blinding. "
        "All participants completed the study with no missing data."
    ),
    "sections": [
        {
            "title": "Methods",
            "page": 1,
            "start": 0,
            "text": (
                "This was a randomized controlled trial with adequate blinding. "
                "All participants completed the study with no missing data."
            ),
        },
    ],
}

_RECORD = {"id": "rec-rob-1", "titulo": "RoB Test", "abstract": "..."}


def test_rob_pipeline_all_low():
    resp, metrics = assess_rob(_DOC, _RECORD, FakeRobLLM())
    assert isinstance(resp.resultado, RobResult)
    assert resp.resultado.instrument == "rob2"
    assert resp.resultado.overall == "low"
    assert len(resp.resultado.domains) == 5
    for d in resp.resultado.domains:
        assert d.judgment == "low"
    assert "latencia_s" in metrics


class HighRiskLLM:
    """Returns N for first question of each domain."""

    def invoke(self, prompt: str):
        import re

        questions = re.findall(r"- (\d+\.\d+):", prompt)
        data = []
        for i, q in enumerate(questions):
            data.append({
                "question_id": q,
                "answer": "N" if i == 0 else "Y",
                "reasoning": "Test reasoning.",
                "evidence_text": "randomized controlled trial with adequate blinding",
            })

        class Resp:
            pass

        r = Resp()
        r.content = json.dumps(data)
        return r


def test_rob_pipeline_high_risk():
    resp, metrics = assess_rob(_DOC, _RECORD, HighRiskLLM())
    assert resp.resultado.overall == "high"
    for d in resp.resultado.domains:
        assert d.judgment in ("high", "some_concerns")
