"""Trava o fracasso conhecido da heurística de suficiência.

O acerto esperado neste conjunto é 1/6, e só o editorial. Se o teste passar a
acertar os seis, alguém overfitou a lista de marcadores ao held-out.
"""
from prismai.tools.sufficiency import pista_heuristica

HOLDOUT = [
    {
        "id": "H01",
        "esperado_suficiente": False,
        "titulo": "Classroom Impressions of a Generative Writing Assistant",
        "abstract": (
            "During one term we let a writing assistant loose in two seminars and simply "
            "jotted down what we noticed. Teaching staff felt that drafts came in tidier and "
            "that a handful of students leaned on it more than we would have liked. We did not "
            "track anything in a structured way and there were no measurements of writing "
            "quality; what follows is a narrative account of impressions gathered informally "
            "over the semester by the two instructors involved."
        ),
    },
    {
        "id": "H02",
        "esperado_suficiente": False,
        "titulo": "Our Experience Deploying a Chat Tutor in a Physics Course",
        "abstract": (
            "This piece recounts how a chat tutor was introduced in an introductory physics "
            "course. Informal feedback from teaching assistants suggested students appreciated "
            "the round-the-clock availability. Our general sense was that engagement rose, "
            "though we never designed an instrument to check it and ran no comparison against "
            "the previous cohort. We share the account so others can learn from the rollout "
            "rather than from any numbers."
        ),
    },
    {
        "id": "H03",
        "esperado_suficiente": False,
        "titulo": "Notes from a Term with an AI Teaching Aide",
        "abstract": (
            "A reflective report on a single term. The instructor kept a diary and reports "
            "impressions rather than findings: some learners seemed more confident, others "
            "disengaged. Nothing was counted, scored or compared, and the diary was not coded "
            "against any framework. Readers should treat the material as a practitioner story "
            "about what it felt like to teach alongside the tool."
        ),
    },
    {
        "id": "H04",
        "esperado_suficiente": True,
        "titulo": "A Randomized Trial of an LLM Tutor on Algebra Achievement",
        "abstract": (
            "We randomized 214 undergraduates to an LLM tutor or standard tutoring and "
            "measured algebra achievement with a validated 40-item instrument at baseline and "
            "at twelve weeks. The intervention group scored 8.4 points higher (95% CI 4.1 to "
            "12.7, p = 0.002). Going beyond anecdotal reports of enthusiasm, we quantified "
            "learning gains directly. We draw no conclusions about retention past one term, "
            "which the present design cannot address."
        ),
    },
    {
        "id": "H05",
        "esperado_suficiente": True,
        "titulo": "Quasi-Experimental Evaluation of AI Feedback on Essay Scores",
        "abstract": (
            "Using a non-equivalent control group design with 180 students across six "
            "sections, we compared essay scores before and after introducing automated AI "
            "feedback. Mean scores rose from 68.2 to 74.9 in the treatment sections against "
            "69.0 to 70.1 in controls, a difference significant at p < 0.01. Earlier work in "
            "this area rested on anecdotal classroom accounts; here we report measured "
            "outcomes with a documented rubric and two blinded raters."
        ),
    },
    {
        "id": "H06",
        "esperado_suficiente": False,
        "esperado_tipo": "nao_empirico",
        "titulo": "Editorial: Why Universities Must Rethink Assessment in the Age of AI",
        "abstract": (
            "In this editorial we argue that assessment practice in higher education has not "
            "kept pace with generative models. We review the pressures facing examiners and "
            "call on institutions to redesign coursework. The argument is normative and draws "
            "on the authors' positions on policy committees rather than on a study of "
            "learners."
        ),
    },
]


def test_heuristica_nao_generaliza():
    obtidos = {reg["id"]: pista_heuristica(reg) for reg in HOLDOUT}

    anedoticos = ["H01", "H02", "H03"]
    assert [i for i in anedoticos if obtidos[i]["suficiente"] is True] == anedoticos

    armadilhas = ["H04", "H05"]
    assert [i for i in armadilhas if obtidos[i]["suficiente"] is False] == armadilhas

    assert obtidos["H06"]["suficiente"] is False
    assert obtidos["H06"]["tipo_insuficiencia"] == "nao_empirico"

    acertos = sum(
        1 for reg in HOLDOUT if obtidos[reg["id"]]["suficiente"] == reg["esperado_suficiente"]
    )
    assert acertos == 1
