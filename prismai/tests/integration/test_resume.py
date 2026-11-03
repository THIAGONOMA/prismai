"""Test idempotent resume: simulates worker dying mid-batch.

Uses InMemoryRepository to prove the logic without Postgres.
"""
from __future__ import annotations

import pytest

from prismai.persistence.memory import InMemoryRepository


@pytest.fixture
def repo():
    return InMemoryRepository()


@pytest.mark.asyncio
async def test_resume_skips_decided_records(repo):
    """If 3 out of 5 records are already decided, only the remaining 2 should be processed."""
    await repo.create_review("rev1")
    all_records = [{"id": f"R{i:02d}", "titulo": f"T{i}", "abstract": f"A{i}"} for i in range(1, 6)]
    await repo.add_records("rev1", all_records)

    # Simulate worker having already decided R01, R02, R03
    for rid in ["R01", "R02", "R03"]:
        await repo.add_decision("rev1", {"registro_id": rid, "decision": "include"})

    # Resume logic: get all records, subtract decided
    records = await repo.get_records("rev1")
    decided = await repo.get_decided_registro_ids("rev1")
    pending = [r for r in records if r["id"] not in decided]

    assert len(pending) == 2
    assert {r["id"] for r in pending} == {"R04", "R05"}


@pytest.mark.asyncio
async def test_resume_no_work_when_all_decided(repo):
    await repo.create_review("rev1")
    all_records = [{"id": f"R{i:02d}", "titulo": f"T{i}", "abstract": f"A{i}"} for i in range(1, 4)]
    await repo.add_records("rev1", all_records)

    for rid in ["R01", "R02", "R03"]:
        await repo.add_decision("rev1", {"registro_id": rid, "decision": "exclude"})

    records = await repo.get_records("rev1")
    decided = await repo.get_decided_registro_ids("rev1")
    pending = [r for r in records if r["id"] not in decided]

    assert len(pending) == 0


@pytest.mark.asyncio
async def test_resume_full_batch_when_none_decided(repo):
    await repo.create_review("rev1")
    all_records = [{"id": f"R{i:02d}", "titulo": f"T{i}", "abstract": f"A{i}"} for i in range(1, 4)]
    await repo.add_records("rev1", all_records)

    records = await repo.get_records("rev1")
    decided = await repo.get_decided_registro_ids("rev1")
    pending = [r for r in records if r["id"] not in decided]

    assert len(pending) == 3
