"""Integration test for the eligibility graph with a fake LLM."""
from __future__ import annotations

import json

from prismai.core.models import EligibilityResult
from prismai.graphs.eligibility import evaluate_eligibility


class FakeLLM:
    """Deterministic LLM: inclusion criteria met, exclusion criteria not met."""

    def invoke(self, prompt: str):
        is_exclusion = "exclusion" in prompt.lower() or "Animal study" in prompt
        met = not is_exclusion

        class Resp:
            pass

        r = Resp()
        r.content = json.dumps({
            "met": met,
            "reasoning": "Evidence found." if met else "No evidence of this criterion.",
            "evidence_text": "randomized controlled trial with 200 participants" if met else "",
        })
        return r


_DOC = {
    "record_id": "rec-1",
    "content_text": (
        "This study investigates cognitive behavioral therapy.\n\n"
        "We conducted a randomized controlled trial with 200 participants."
    ),
    "sections": [
        {"title": "Introduction", "page": 1, "start": 0,
         "text": "This study investigates cognitive behavioral therapy."},
        {"title": "Methods", "page": 3, "start": 55,
         "text": "We conducted a randomized controlled trial with 200 participants."},
    ],
}

_PROTOCOL = {
    "pergunta": "Is CBT effective for depression?",
    "P": "Adults with depression",
    "I": "CBT",
    "C": "Waitlist",
    "O": "HAM-D improvement",
    "desenho": "RCT",
    "inclusao": ["Randomized controlled trial", "Depression outcome measured"],
    "exclusao": ["Animal study"],
}

_RECORD = {"id": "rec-1", "titulo": "CBT for Depression", "abstract": "...", "doi": "10.1234/test"}


def test_eligibility_pipeline_include():
    resp, metrics = evaluate_eligibility(_DOC, _RECORD, _PROTOCOL, FakeLLM())
    assert isinstance(resp.resultado, EligibilityResult)
    assert resp.resultado.decision == "include"
    assert resp.resultado.confidence == "high"
    assert len(resp.resultado.criteria_results) == 3  # 2 inclusion + 1 exclusion


class ExcludingLLM:
    """LLM that says exclusion criterion (Animal study) is met."""

    def __init__(self):
        self._call_count = 0

    def invoke(self, prompt: str):
        self._call_count += 1
        if "Animal study" in prompt:
            content = json.dumps({
                "met": True,
                "reasoning": "This is an animal study.",
                "evidence_text": "randomized controlled trial with 200 participants",
            })
        else:
            content = json.dumps({
                "met": True,
                "reasoning": "Criterion met.",
                "evidence_text": "randomized controlled trial with 200 participants",
            })

        class Resp:
            pass

        r = Resp()
        r.content = content
        return r


def test_eligibility_pipeline_exclude():
    resp, metrics = evaluate_eligibility(_DOC, _RECORD, _PROTOCOL, ExcludingLLM())
    assert resp.resultado.decision == "exclude"
    assert resp.resultado.exclusion_reason is not None
    assert "Animal study" in resp.resultado.exclusion_reason
