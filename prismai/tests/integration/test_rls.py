"""Test RLS isolation between orgs.

Requires DATABASE_URL_TEST pointing to a Postgres instance.
Skipped automatically when not available.
"""
from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio

pytestmark = pytest.mark.postgres

postgres_available = bool(os.environ.get("DATABASE_URL_TEST"))
if not postgres_available:
    pytest.skip("DATABASE_URL_TEST not set", allow_module_level=True)


@pytest_asyncio.fixture
async def pg_setup():
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from prismai.persistence.models_db import Base

    url = os.environ["DATABASE_URL_TEST"]
    admin_engine = create_async_engine(url, echo=False)

    async with admin_engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)

        for table in ["reviews", "protocols", "records", "decisions", "traces", "jobs"]:
            await conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
            await conn.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
            await conn.execute(text(
                f"CREATE POLICY tenant_isolation_{table} ON {table} "
                f"USING (org_id::text = current_setting('app.current_org', true)) "
                f"WITH CHECK (org_id::text = current_setting('app.current_org', true))"
            ))

        org_a_id = uuid.uuid4()
        org_b_id = uuid.uuid4()
        await conn.execute(
            text("INSERT INTO orgs (id, name) VALUES (:id, :name)"),
            [{"id": org_a_id, "name": "Org A"}, {"id": org_b_id, "name": "Org B"}],
        )

    session_factory = async_sessionmaker(admin_engine, expire_on_commit=False)

    yield {
        "engine": admin_engine,
        "session_factory": session_factory,
        "org_a_id": str(org_a_id),
        "org_b_id": str(org_b_id),
    }

    await admin_engine.dispose()


async def _create_review(sf, org_id: str, slug: str):
    from sqlalchemy import text

    async with sf() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.current_org', :v, true)"), {"v": org_id},
            )
            await session.execute(
                text("INSERT INTO reviews (id, org_id, slug) VALUES (:id, :org_id, :slug)"),
                {"id": uuid.uuid4(), "org_id": uuid.UUID(org_id), "slug": slug},
            )


async def _count_reviews(sf, org_id: str) -> int:
    from sqlalchemy import text

    async with sf() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.current_org', :v, true)"), {"v": org_id},
            )
            result = await session.execute(text("SELECT count(*) FROM reviews"))
            return result.scalar()


@pytest.mark.asyncio
async def test_org_a_cannot_see_org_b_reviews(pg_setup):
    sf = pg_setup["session_factory"]
    org_a = pg_setup["org_a_id"]
    org_b = pg_setup["org_b_id"]

    await _create_review(sf, org_a, "review-a")
    await _create_review(sf, org_b, "review-b")

    assert await _count_reviews(sf, org_a) == 1
    assert await _count_reviews(sf, org_b) == 1


@pytest.mark.asyncio
async def test_no_context_sees_nothing(pg_setup):
    from sqlalchemy import text

    sf = pg_setup["session_factory"]
    await _create_review(sf, pg_setup["org_a_id"], "review-c")

    async with sf() as session:
        async with session.begin():
            result = await session.execute(text("SELECT count(*) FROM reviews"))
            count = result.scalar()
    assert count == 0


@pytest.mark.asyncio
async def test_org_b_cannot_insert_as_org_a(pg_setup):
    from sqlalchemy import text

    sf = pg_setup["session_factory"]
    org_a = pg_setup["org_a_id"]
    org_b = pg_setup["org_b_id"]

    async with sf() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.current_org', :v, true)"), {"v": org_b},
            )
            try:
                await session.execute(
                    text("INSERT INTO reviews (id, org_id, slug) VALUES (:id, :org_id, :slug)"),
                    {"id": uuid.uuid4(), "org_id": uuid.UUID(org_a), "slug": "sneaky"},
                )
                inserted = True
            except Exception:
                inserted = False

    assert not inserted, "Org B should not be able to insert with org A's org_id"
