"""Unit tests for RoB 2 domain judgment and overall judgment."""
from __future__ import annotations

from prismai.checks.rob2 import ROB2_DOMAINS, julgar_dominio, julgar_geral


def test_all_yes_is_low():
    answers = [{"answer": "Y"}, {"answer": "Y"}, {"answer": "PY"}]
    assert julgar_dominio("D1", answers) == "low"


def test_ni_never_low():
    answers = [{"answer": "Y"}, {"answer": "NI"}]
    assert julgar_dominio("D1", answers) != "low"
    assert julgar_dominio("D1", answers) == "some_concerns"


def test_n_produces_high():
    answers = [{"answer": "Y"}, {"answer": "N"}]
    assert julgar_dominio("D1", answers) == "high"


def test_pn_produces_some_concerns_d1():
    answers = [{"answer": "Y"}, {"answer": "PN"}]
    assert julgar_dominio("D1", answers) == "some_concerns"


def test_n_produces_high_d2():
    answers = [{"answer": "Y"}, {"answer": "N"}]
    assert julgar_dominio("D2", answers) == "high"


def test_pn_produces_some_concerns_d2():
    answers = [{"answer": "Y"}, {"answer": "PN"}]
    assert julgar_dominio("D2", answers) == "some_concerns"


def test_only_py_is_low():
    answers = [{"answer": "PY"}, {"answer": "PY"}]
    assert julgar_dominio("D3", answers) == "low"


def test_overall_all_low():
    judgments = ["low", "low", "low", "low", "low"]
    assert julgar_geral(judgments) == "low"


def test_overall_any_high():
    judgments = ["low", "low", "high", "low", "low"]
    assert julgar_geral(judgments) == "high"


def test_overall_three_some_concerns():
    judgments = ["some_concerns", "some_concerns", "some_concerns", "low", "low"]
    assert julgar_geral(judgments) == "high"


def test_overall_two_some_concerns():
    judgments = ["some_concerns", "some_concerns", "low", "low", "low"]
    assert julgar_geral(judgments) == "some_concerns"


def test_overall_one_some_concerns():
    judgments = ["some_concerns", "low", "low", "low", "low"]
    assert julgar_geral(judgments) == "some_concerns"


def test_rob2_has_five_domains():
    assert len(ROB2_DOMAINS) == 5


def test_each_domain_has_questions():
    for d in ROB2_DOMAINS:
        assert "questions" in d
        assert len(d["questions"]) > 0


def test_ni_only_is_some_concerns():
    answers = [{"answer": "NI"}, {"answer": "NI"}]
    assert julgar_dominio("D4", answers) == "some_concerns"


def test_mixed_ni_and_y_is_some_concerns():
    answers = [{"answer": "Y"}, {"answer": "PY"}, {"answer": "NI"}]
    result = julgar_dominio("D5", answers)
    assert result == "some_concerns"
