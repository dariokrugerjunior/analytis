"""Base utilities shared by repositories."""

from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.persistence.orm.base import Base


async def upsert(
    session: AsyncSession,
    model: type[Base],
    values: dict[str, Any],
    conflict_cols: list[str],
    update_cols: list[str],
) -> None:
    """Idempotent UPSERT helper using ON CONFLICT DO UPDATE."""
    stmt = pg_insert(model).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=conflict_cols,
        set_={c: getattr(stmt.excluded, c) for c in update_cols},
    )
    await session.execute(stmt)
