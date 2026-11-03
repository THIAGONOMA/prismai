"""Shared helpers for the SAQ worker process."""
from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prismai.config import settings

_engine = None
_session_factory = None


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _engine, _session_factory  # noqa: PLW0603
    if _session_factory is None:
        _engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _session_factory


async def notify_progress(
    sf: async_sessionmaker[AsyncSession],
    job_id: str,
    progress: int,
    total: int,
    *,
    done: bool = False,
) -> None:
    """Update job row and emit pg_notify for SSE consumers."""
    async with sf() as session:
        async with session.begin():
            status = "completed" if done else "running"
            await session.execute(
                text("UPDATE jobs SET progress = :p, total = :t, status = :s WHERE id::text = :jid"),
                {"p": progress, "t": total, "s": status, "jid": job_id},
            )
            payload = json.dumps({
                "type": "done" if done else "progress",
                "job_id": job_id,
                "progress": progress,
                "total": total,
            })
            await session.execute(text("SELECT pg_notify('job_events', :payload)"), {"payload": payload})
