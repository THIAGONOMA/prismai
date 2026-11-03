"""Fixtures para testes de integração – sem rede, sem API key."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from langchain_core.messages import AIMessage

GOLDEN_DIR = Path(__file__).resolve().parents[2] / "src" / "prismai" / "eval" / "golden"

# ---------------------------------------------------------------------------
# Respostas pré-gravadas do triador (uma por registro)
# ---------------------------------------------------------------------------
RESPOSTAS_FAKE: dict[str, str] = {
    "R01": '{"decision":"include","reasons":["P: undergraduate students (alunos de graduação)","I: GPT-based tutoring chatbot (LLM)","O: academic performance (final exam scores)","desenho: quasi-experimental study"],"evidence":["quasi-experimental study evaluated the impact of a GPT-based tutoring chatbot","academic performance of 120 undergraduate students enrolled in Calculus I","Final exam scores were compared using ANCOVA"],"confidence":"high"}',
    "R02": '{"decision":"exclude","reasons":["P: ensino médio, não graduação","I: tutoria presencial humana, sem LLM"],"evidence":["alunos do ensino médio","tutoria presencial conduzida por monitores humanos","Nenhuma tecnologia de inteligência artificial foi utilizada"],"confidence":"high"}',
    "R03": '{"decision":"exclude","reasons":["O: apenas satisfação e percepção, sem desempenho acadêmico"],"evidence":["No academic performance data were collected","focused exclusively on student perceptions and attitudes"],"confidence":"high"}',
    "R04": '{"decision":"include","reasons":["P: undergraduate biology students","I: ChatGPT (LLM)","O: pre- and post-test scores"],"evidence":["45 undergraduate biology students used ChatGPT","Pre- and post-test scores on a standardized biology knowledge assessment"],"confidence":"high"}',
    "R05": '{"decision":"uncertain","reasons":["Abstract vazio, informação insuficiente para avaliar"],"evidence":[],"confidence":"low"}',
    "R06": '{"decision":"exclude","reasons":["desenho: editorial, sem dados empíricos"],"evidence":["This editorial discusses","No empirical data are presented"],"confidence":"high"}',
    "R07": '{"decision":"include","reasons":["P: undergraduate students","I: LLM-assisted homework platform","O: exam scores"],"evidence":["540 undergraduate students participated","LLM-assisted homework platform on exam scores","LLM group showed higher exam scores"],"confidence":"high"}',
    "R08": '{"decision":"exclude","reasons":["P: profissionais de vendas, não graduação"],"evidence":["profissionais de vendas em uma empresa multinacional","treinamento corporativo"],"confidence":"high"}',
    "R09": '{"decision":"uncertain","reasons":["I: tecnologia não nomeada como LLM especificamente"],"evidence":["coding assistant powered by recent AI advances","specific technology was not named"],"confidence":"medium"}',
    "R10": '{"decision":"include","reasons":["P: alunos de graduação","I: tutor baseado em GPT-4 (LLM)","O: notas e retenção"],"evidence":["alunos de graduação em estatística","tutor baseado em GPT-4","notas médias superiores","menor taxa de reprovação"],"confidence":"high"}',
    "R11": '{"decision":"include","reasons":["P: undergraduate chemistry students","I: LLM-based tutor","O: final course grades"],"evidence":["200 undergraduate chemistry students","LLM-based tutor for weekly problem-solving sessions","mean GPA of 3.1 compared to 2.7"],"confidence":"high"}',
    "R12": '{"decision":"uncertain","reasons":["dados insuficientes, sem coleta sistemática"],"evidence":[],"confidence":"low"}',
    "R13": '{"decision":"include","reasons":["P: alunos de graduação noturno","I: tutor baseado em LLM","O: notas e aprovação"],"evidence":["alunos do curso noturno de Engenharia de Producao","tutor LLM para resolucao de exercicios de Calculo I","media 6.8 (DP=1.3) contra 5.9 (DP=1.5) do controle"],"confidence":"high"}',
}


class FakeLLM:
    """LLM falso que devolve respostas pré-gravadas baseadas no registro_id presente no prompt."""

    def invoke(self, messages, **kwargs) -> AIMessage:
        prompt_text = " ".join(m.content for m in messages if hasattr(m, "content"))
        for rid, response in RESPOSTAS_FAKE.items():
            if rid in prompt_text:
                return AIMessage(content=response)
        return AIMessage(
            content='{"decision":"uncertain","reasons":["Fallback"],"evidence":[],"confidence":"low"}'
        )


class FakeAuditorLLM:
    """LLM falso para o auditor – simplesmente devolve o mesmo JSON do triador."""

    def invoke(self, messages, **kwargs) -> AIMessage:
        prompt_text = " ".join(m.content for m in messages if hasattr(m, "content"))
        for rid, response in RESPOSTAS_FAKE.items():
            if rid in prompt_text:
                return AIMessage(content=response)
        return AIMessage(
            content='{"decision":"uncertain","reasons":["Fallback"],"evidence":[],"confidence":"low"}'
        )


# ---------------------------------------------------------------------------
# Helpers para carregar golden set
# ---------------------------------------------------------------------------
def _load_yaml(name: str) -> dict | list:
    return yaml.safe_load((GOLDEN_DIR / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Fixtures pytest
# ---------------------------------------------------------------------------
@pytest.fixture()
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture()
def fake_auditor_llm() -> FakeAuditorLLM:
    return FakeAuditorLLM()


@pytest.fixture()
def protocolo() -> dict:
    return _load_yaml("protocolo.yaml")


@pytest.fixture()
def registros() -> list[dict]:
    return _load_yaml("registros.yaml")


@pytest.fixture()
def registros_map(registros) -> dict[str, dict]:
    return {r["id"]: r for r in registros}


@pytest.fixture()
def casos() -> list[dict]:
    return _load_yaml("casos.yaml")


@pytest.fixture()
def casos_map(casos) -> dict[str, dict]:
    return {c["id"]: c for c in casos}


@pytest.fixture()
def triador_outputs() -> dict[str, dict]:
    """Retorna o dict de saída do triador para cada registro, parseado do JSON fake."""
    return {rid: json.loads(raw) for rid, raw in RESPOSTAS_FAKE.items()}
