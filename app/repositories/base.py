"""Generic async repository helpers: CRUD + cursor pagination (spec §16)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, tuple_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.utils import decode_cursor, encode_cursor


class BaseRepository:
    """Cursor-paginated repository bound to an async session."""

    model: type
    pk_attr: str = "id"
    order_attr: str = "created_at"

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- CRUD -----------------------------------------------------------------

    async def get(self, pk: Any):
        return await self.session.get(self.model, pk)

    def add(self, instance) -> None:
        self.session.add(instance)

    async def flush(self) -> None:
        await self.session.flush()

    async def delete(self, pk: Any) -> int:
        result = await self.session.execute(
            delete(self.model).where(getattr(self.model, self.pk_attr) == pk)
        )
        return result.rowcount or 0

    # --- Pagination ---------------------------------------------------------------

    def _base_stmt(self, conditions: list[Any] | None = None) -> Select:
        stmt = Select(self.model)
        for cond in conditions or []:
            stmt = stmt.where(cond)
        return stmt

    async def list_page(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
        conditions: list[Any] | None = None,
        descending: bool = True,
    ) -> tuple[list, str | None]:
        """Return (items, next_cursor) ordered by (order_attr, pk)."""
        order_col = getattr(self.model, self.order_attr)
        pk_col = getattr(self.model, self.pk_attr)
        stmt = self._base_stmt(conditions)
        if cursor:
            ts, pk_value = decode_cursor(cursor)
            row = (ts, pk_value)
            stmt = stmt.where(
                tuple_(order_col, pk_col) < row if descending else tuple_(order_col, pk_col) > row
            )
        stmt = stmt.order_by(
            order_col.desc() if descending else order_col.asc(),
            pk_col.desc() if descending else pk_col.asc(),
        ).limit(limit + 1)
        rows = list((await self.session.execute(stmt)).scalars().all())
        next_cursor = None
        if len(rows) > limit:
            rows = rows[:limit]
            last = rows[-1]
            ts = getattr(last, self.order_attr)
            if isinstance(ts, datetime):
                next_cursor = encode_cursor(ts, getattr(last, self.pk_attr))
        return rows, next_cursor

    async def count(self, conditions: list[Any] | None = None) -> int:
        stmt = Select(func.count()).select_from(self.model)
        for cond in conditions or []:
            stmt = stmt.where(cond)
        total = await self.session.scalar(stmt)
        return int(total or 0)


def as_uuid(value: str | uuid.UUID) -> uuid.UUID:
    """Coerce a string path parameter to UUID."""
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))