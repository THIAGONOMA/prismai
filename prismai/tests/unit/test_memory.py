import pytest

from prismai.persistence.memory import InMemoryRepository


@pytest.fixture
def repo():
    return InMemoryRepository()


class TestInMemoryRepository:
    @pytest.mark.asyncio
    async def test_create_and_get_review(self, repo):
        review = await repo.create_review("rev1")
        assert review["id"] == "rev1"
        fetched = await repo.get_review("rev1")
        assert fetched["id"] == "rev1"

    @pytest.mark.asyncio
    async def test_duplicate_create_raises(self, repo):
        await repo.create_review("rev1")
        with pytest.raises(ValueError, match="already exists"):
            await repo.create_review("rev1")

    @pytest.mark.asyncio
    async def test_set_and_get_protocol(self, repo):
        await repo.create_review("rev1")
        proto = {"pergunta": "test?"}
        await repo.set_protocol("rev1", proto)
        assert await repo.get_protocol("rev1") == proto

    @pytest.mark.asyncio
    async def test_add_and_get_records(self, repo):
        await repo.create_review("rev1")
        count = await repo.add_records("rev1", [{"id": "r1"}, {"id": "r2"}])
        assert count == 2
        assert len(await repo.get_records("rev1")) == 2

    @pytest.mark.asyncio
    async def test_add_and_get_decisions(self, repo):
        await repo.create_review("rev1")
        await repo.add_decision("rev1", {"decision": "include", "registro_id": "r1"})
        decisions = await repo.get_decisions("rev1")
        assert len(decisions) == 1
        assert decisions[0]["decision"] == "include"

    @pytest.mark.asyncio
    async def test_get_decided_registro_ids(self, repo):
        await repo.create_review("rev1")
        await repo.add_decision("rev1", {"decision": "include", "registro_id": "r1"})
        await repo.add_decision("rev1", {"decision": "exclude", "registro_id": "r2"})
        ids = await repo.get_decided_registro_ids("rev1")
        assert ids == {"r1", "r2"}

    @pytest.mark.asyncio
    async def test_nonexistent_review_raises_on_set_protocol(self, repo):
        with pytest.raises(KeyError, match="not found"):
            await repo.set_protocol("nope", {})

    @pytest.mark.asyncio
    async def test_nonexistent_review_raises_on_add_records(self, repo):
        with pytest.raises(KeyError, match="not found"):
            await repo.add_records("nope", [])

    @pytest.mark.asyncio
    async def test_nonexistent_review_raises_on_add_decision(self, repo):
        with pytest.raises(KeyError, match="not found"):
            await repo.add_decision("nope", {})

    @pytest.mark.asyncio
    async def test_get_review_nonexistent_returns_none(self, repo):
        assert await repo.get_review("nope") is None

    @pytest.mark.asyncio
    async def test_deep_copy_isolation(self, repo):
        await repo.create_review("rev1")
        proto = {"pergunta": "test?", "items": [1, 2]}
        await repo.set_protocol("rev1", proto)
        proto["items"].append(3)
        fetched = await repo.get_protocol("rev1")
        assert len(fetched["items"]) == 2
