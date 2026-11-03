from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from prismai.persistence.memory import InMemoryRepository
from prismai.persistence.repository import ReviewRepository

_repo: ReviewRepository | None = None


def get_repo() -> ReviewRepository:
    global _repo  # noqa: PLW0603
    if _repo is None:
        _repo = InMemoryRepository()
    return _repo


def reset_repo() -> None:
    global _repo  # noqa: PLW0603
    _repo = InMemoryRepository()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a raw DB session for operations that need direct SQL access (e.g. dedup)."""
    from prismai.persistence.engine import async_session_factory

    async with async_session_factory() as session:
        yield session
