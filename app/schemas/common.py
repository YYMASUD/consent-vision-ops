"""Generic pagination envelope (spec §16: cursor pagination)."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Cursor-paginated result set."""

    items: list[T]
    next_cursor: str | None = None
    total: int | None = None