from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from prismai.config import settings

engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
admin_engine = create_async_engine(settings.database_url_admin, echo=False, pool_pre_ping=True)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
admin_session_factory = async_sessionmaker(admin_engine, expire_on_commit=False)


async def get_session(org_id: str | None = None) -> AsyncGenerator[AsyncSession, None]:
    """Yield a session with optional RLS tenant context."""
    async with async_session_factory() as session:
        async with session.begin():
            if org_id is not None:
                await session.execute(
                    text("SELECT set_config('app.current_org', :v, true)"),
                    {"v": str(org_id)},
                )
            yield session


async def dispose_engines() -> None:
    await engine.dispose()
    await admin_engine.dispose()
