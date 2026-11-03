"""Integration tests for the synthesis pipeline (M6)."""
from __future__ import annotations

import json

from prismai.graphs.synthesis import synthesize


class FakeLLMSynthesis:
    """Returns mapping that includes all studies."""
    def invoke(self, prompt):
        class Resp:
            content = json.dumps([
                {"record_id": "s1", "incluido": True},
                {"record_id": "s2", "incluido": True},
                {"record_id": "s3", "incluido": True},
            ])
        return Resp()


def _make_extraction(record_id, n_int, n_ctrl, m_int, sd_int, m_ctrl, sd_ctrl):
    return {
        "record_id": record_id,
        "status": "completed",
        "cells": [
            {"field": "n_intervencao", "value": n_int},
            {"field": "n_controle", "value": n_ctrl},
            {"field": "media_intervencao", "value": m_int},
            {"field": "dp_intervencao", "value": sd_int},
            {"field": "media_controle", "value": m_ctrl},
            {"field": "dp_controle", "value": sd_ctrl},
            {"field": "desfecho_primario", "value": "Pain score"},
        ],
    }


class TestSynthesisPipeline:
    def test_pooled_effect_direction(self):
        config = {
            "version": "v1",
            "outcomes": [{"key": "pain", "nome": "Pain", "tipo": "continuous", "measure": "smd"}],
        }
        extractions = [
            _make_extraction("s1", 30, 30, 5.0, 2.0, 3.0, 2.0),
            _make_extraction("s2", 40, 40, 4.5, 1.5, 3.5, 1.5),
            _make_extraction("s3", 25, 25, 6.0, 2.5, 4.0, 2.5),
        ]
        rob = [
            {"record_id": "s1", "overall_judgment": "low"},
            {"record_id": "s2", "overall_judgment": "low"},
            {"record_id": "s3", "overall_judgment": "low"},
        ]
        envelopes, metricas = synthesize(config, extractions, rob, {}, FakeLLMSynthesis())
        assert len(envelopes) == 1
        sr = envelopes[0].resultado
        assert sr.pooled_effect is not None
        assert sr.pooled_effect > 0  # intervention better
        assert sr.k_studies == 3

    def test_empty_config_returns_empty(self):
        config = {"version": "v1", "outcomes": []}
        envelopes, _ = synthesize(config, [], [], {}, FakeLLMSynthesis())
        assert len(envelopes) == 0
