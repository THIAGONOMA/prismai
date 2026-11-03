"""Testes E2E da API REST – sem rede, sem API key."""
from __future__ import annotations

import httpx
import pytest

from prismai.api.deps import reset_repo
from prismai.api.jobs import reset_jobs
from prismai.api.main import app


@pytest.fixture(autouse=True)
def _limpa_estado():
    """Reseta repositório e jobs antes de cada teste."""
    reset_repo()
    reset_jobs()
    yield
    reset_repo()
    reset_jobs()


@pytest.fixture()
def client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
REVIEW_ID = "test-review"


def _protocolo_payload() -> dict:
    return {
        "pergunta": "Tutores baseados em LLM melhoram o desempenho acadêmico?",
        "P": "alunos de graduação",
        "I": "tutor ou chatbot baseado em LLM",
        "C": "ensino tradicional",
        "O": "desempenho acadêmico (nota, aprovação ou retenção)",
        "desenho": "estudo empírico",
        "inclusao": ["Envolve alunos de graduação", "Usa LLM"],
        "exclusao": ["População não é graduação"],
    }


def _records_payload() -> dict:
    records = [
        {"id": f"R{i:02d}", "titulo": f"Título R{i:02d}", "abstract": f"Abstract do registro R{i:02d}."}
        for i in range(1, 13)
    ]
    return {"records": records}


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_healthz(client):
    async with client:
        r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_criar_review(client):
    async with client:
        r = await client.post("/v1/reviews", json={"id": REVIEW_ID})
    assert r.status_code == 201
    assert r.json()["id"] == REVIEW_ID


@pytest.mark.asyncio
async def test_review_duplicada_retorna_409(client):
    async with client:
        await client.post("/v1/reviews", json={"id": REVIEW_ID})
        r = await client.post("/v1/reviews", json={"id": REVIEW_ID})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_protocol_review_inexistente_retorna_404(client):
    async with client:
        r = await client.post("/v1/reviews/inexistente/protocol", json=_protocolo_payload())
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_set_e_get_protocol(client):
    async with client:
        await client.post("/v1/reviews", json={"id": REVIEW_ID})
        r = await client.post(f"/v1/reviews/{REVIEW_ID}/protocol", json=_protocolo_payload())
        assert r.status_code == 200

        r = await client.get(f"/v1/reviews/{REVIEW_ID}/protocol")
        assert r.status_code == 200
        proto = r.json()
        assert proto["P"] == "alunos de graduação"


@pytest.mark.asyncio
async def test_get_protocol_sem_setar_retorna_404(client):
    async with client:
        await client.post("/v1/reviews", json={"id": REVIEW_ID})
        r = await client.get(f"/v1/reviews/{REVIEW_ID}/protocol")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_importar_records(client):
    async with client:
        await client.post("/v1/reviews", json={"id": REVIEW_ID})
        r = await client.post(f"/v1/reviews/{REVIEW_ID}/records", json=_records_payload())
        assert r.status_code == 200
        assert r.json()["imported"] == 12


@pytest.mark.asyncio
async def test_records_review_inexistente_retorna_404(client):
    async with client:
        r = await client.post("/v1/reviews/inexistente/records", json=_records_payload())
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_decisions_vazio_inicialmente(client):
    async with client:
        await client.post("/v1/reviews", json={"id": REVIEW_ID})
        r = await client.get(f"/v1/reviews/{REVIEW_ID}/decisions")
        assert r.status_code == 200
        assert r.json() == []


@pytest.mark.asyncio
async def test_traces_vazio_inicialmente(client):
    async with client:
        await client.post("/v1/reviews", json={"id": REVIEW_ID})
        r = await client.get(f"/v1/reviews/{REVIEW_ID}/traces")
        assert r.status_code == 200
        assert r.json() == []


@pytest.mark.asyncio
async def test_fluxo_crud_completo(client):
    """Exercita POST review → protocol → records → GET protocol/decisions/traces."""
    async with client:
        r = await client.post("/v1/reviews", json={"id": REVIEW_ID})
        assert r.status_code == 201

        r = await client.post(f"/v1/reviews/{REVIEW_ID}/protocol", json=_protocolo_payload())
        assert r.status_code == 200

        r = await client.post(f"/v1/reviews/{REVIEW_ID}/records", json=_records_payload())
        assert r.status_code == 200
        assert r.json()["imported"] == 12

        r = await client.get(f"/v1/reviews/{REVIEW_ID}/protocol")
        assert r.status_code == 200
        assert r.json()["pergunta"] == _protocolo_payload()["pergunta"]

        r = await client.get(f"/v1/reviews/{REVIEW_ID}/decisions")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

        r = await client.get(f"/v1/reviews/{REVIEW_ID}/traces")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
