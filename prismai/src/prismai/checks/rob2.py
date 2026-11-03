"""RoB 2 domain definitions and deterministic judgment logic."""
from __future__ import annotations


def _q(qid: str, text: str) -> dict:
    return {"id": qid, "text": text}


ROB2_DOMAINS: list[dict] = [
    {
        "id": "D1",
        "name": "Randomization process",
        "description": "Bias arising from the randomization process",
        "questions": [
            _q("1.1", "Was the allocation sequence random?"),
            _q("1.2", "Was the allocation sequence concealed until participants were enrolled?"),
            _q("1.3", "Did baseline differences suggest a problem with randomization?"),
        ],
    },
    {
        "id": "D2",
        "name": "Deviations from intended interventions",
        "description": "Bias due to deviations from intended interventions",
        "questions": [
            _q("2.1", "Were participants aware of their assigned intervention?"),
            _q("2.2", "Were carers/deliverers aware of the assigned intervention?"),
            _q("2.3", "Were there deviations from intended intervention due to trial context?"),
            _q("2.4", "Were these deviations likely to have affected the outcome?"),
            _q("2.5", "Were deviations from intended intervention balanced between groups?"),
            _q("2.6", "Was an appropriate analysis used to estimate assignment effect?"),
            _q("2.7", "Was there potential for a substantial impact on the result?"),
        ],
    },
    {
        "id": "D3",
        "name": "Missing outcome data",
        "description": "Bias due to missing outcome data",
        "questions": [
            _q("3.1", "Were data available for all or nearly all participants randomized?"),
            _q("3.2", "Is there evidence the result was not biased by missing outcome data?"),
            _q("3.3", "Could missingness in the outcome depend on its true value?"),
            _q("3.4", "Is it likely that missingness depended on its true value?"),
        ],
    },
    {
        "id": "D4",
        "name": "Measurement of the outcome",
        "description": "Bias in measurement of the outcome",
        "questions": [
            _q("4.1", "Was the method of measuring the outcome inappropriate?"),
            _q("4.2", "Could measurement of the outcome have differed between groups?"),
            _q("4.3", "Were outcome assessors aware of intervention received?"),
            _q("4.4", "Could assessment be influenced by knowledge of intervention?"),
            _q("4.5", "Is it likely assessment was influenced by knowledge of intervention?"),
        ],
    },
    {
        "id": "D5",
        "name": "Selection of the reported result",
        "description": "Bias in selection of the reported result",
        "questions": [
            _q("5.1", "Were data analysed per a pre-specified analysis plan?"),
            _q("5.2", "Is the result likely selected from multiple outcome measurements?"),
            _q("5.3", "Is the result likely selected from multiple eligible analyses?"),
        ],
    },
]


def julgar_dominio(domain_id: str, answers: list[dict]) -> str:
    """Map signalling question answers to domain judgment.

    NI (No Information) never produces 'low' — minimum is some_concerns.
    """
    answer_set = {a.get("answer", "NI") for a in answers}

    has_ni = "NI" in answer_set

    if any(a in answer_set for a in ("N", "PN")):
        if domain_id in ("D1", "D3"):
            if "N" in answer_set:
                return "high"
            return "some_concerns"
        return "high" if "N" in answer_set else "some_concerns"

    if has_ni:
        return "some_concerns"

    if answer_set <= {"Y", "PY"}:
        return "low"

    return "some_concerns"


def julgar_geral(domain_judgments: list[str]) -> str:
    """Combine domain judgments into overall RoB judgment.

    low if all low; high if any high or 3+ some_concerns; else some_concerns.
    """
    if all(j == "low" for j in domain_judgments):
        return "low"
    n_high = sum(1 for j in domain_judgments if j == "high")
    n_concerns = sum(1 for j in domain_judgments if j == "some_concerns")
    if n_high >= 1 or n_concerns >= 3:
        return "high"
    return "some_concerns"
