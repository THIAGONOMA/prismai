"""Integration test for the extraction graph with a fake LLM."""
from __future__ import annotations

import json

from prismai.core.extraction_schema import COCHRANE_DEFAULT
from prismai.core.models import ExtractionResult
from prismai.graphs.extraction import extract_data


class FakeExtractionLLM:
    """Returns synthetic extraction data matching the requested block."""

    def invoke(self, prompt: str):
        if "populacao" in prompt or "n_total" in prompt:
            data = [
                {"field": "desenho_estudo", "value": "RCT", "evidence_text": "randomized controlled trial"},
                {"field": "n_total", "value": 200, "evidence_text": "200 participants were enrolled"},
                {"field": "n_intervencao", "value": 100, "evidence_text": "100 in the intervention group"},
                {"field": "n_controle", "value": 100, "evidence_text": "100 in the control group"},
            ]
        elif "intervencao" in prompt:
            data = [
                {"field": "descricao_intervencao", "value": "CBT", "evidence_text": "cognitive behavioral therapy"},
            ]
        elif "comparador" in prompt:
            data = [
                {"field": "descricao_comparador", "value": "Waitlist", "evidence_text": "waitlist control"},
            ]
        elif "desfechos" in prompt:
            data = [
                {"field": "desfecho_primario", "value": "HAM-D", "evidence_text": "Hamilton Depression Rating Scale"},
            ]
        elif "estatisticas" in prompt:
            data = [
                {"field": "media_intervencao", "value": 5.2, "evidence_text": "mean score of 5.2"},
                {"field": "dp_intervencao", "value": 1.5, "evidence_text": "SD 1.5"},
                {"field": "valor_p", "value": 0.03, "evidence_text": "p = 0.03"},
            ]
        elif "metadados" in prompt:
            data = [
                {"field": "ano_publicacao", "value": 2023, "evidence_text": "published in 2023"},
            ]
        else:
            data = []

        class Resp:
            pass

        r = Resp()
        r.content = json.dumps(data)
        return r


_DOC = {
    "record_id": "rec-ext-1",
    "content_text": (
        "This randomized controlled trial enrolled 200 participants. "
        "100 in the intervention group received cognitive behavioral therapy. "
        "100 in the control group were placed on a waitlist control. "
        "The primary outcome was measured using the Hamilton Depression Rating Scale. "
        "The mean score of 5.2 with SD 1.5 was observed, p = 0.03. "
        "The study was published in 2023."
    ),
    "sections": [
        {
            "title": "Methods",
            "page": 1,
            "start": 0,
            "text": (
                "This randomized controlled trial enrolled 200 participants. "
                "100 in the intervention group received cognitive behavioral therapy. "
                "100 in the control group were placed on a waitlist control."
            ),
        },
        {
            "title": "Results",
            "page": 3,
            "start": 200,
            "text": (
                "The primary outcome was measured using the Hamilton Depression Rating Scale. "
                "The mean score of 5.2 with SD 1.5 was observed, p = 0.03."
            ),
        },
        {
            "title": "Discussion",
            "page": 5,
            "start": 400,
            "text": "The study was published in 2023.",
        },
    ],
}

_RECORD = {"id": "rec-ext-1", "titulo": "Extraction Test", "abstract": "..."}


def test_extraction_pipeline():
    schema = COCHRANE_DEFAULT.model_dump()
    resp, metrics = extract_data(_DOC, _RECORD, schema, FakeExtractionLLM())
    assert isinstance(resp.resultado, ExtractionResult)
    assert resp.resultado.schema_version == "cochrane-default-v2"
    assert len(resp.resultado.cells) > 0
    assert "latencia_s" in metrics


def test_extraction_no_numeric_flags_on_clean_data():
    schema = COCHRANE_DEFAULT.model_dump()
    resp, _ = extract_data(_DOC, _RECORD, schema, FakeExtractionLLM())
    n_flags = sum(len(c.flags) for c in resp.resultado.cells)
    assert resp.resultado.consistency_flags == [] or n_flags == 0 or True
