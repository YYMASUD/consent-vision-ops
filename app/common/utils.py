"""Shared runtime utilities: clock, IDs, request context, error types."""
from __future__ import annotations

import base64
import contextvars
import itertools
import uuid
from datetime import UTC, datetime

# --- Clock -------------------------------------------------------------------


def utcnow() -> datetime:
    """Timezone-aware UTC now."""
    return datetime.now(UTC)


def parse_dt(value: str | datetime | None) -> datetime | None:
    """Parse ISO datetime strings safely."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def iso(value: datetime | None) -> str | None:
    """ISO-8601 string."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


# --- IDs ---------------------------------------------------------------------

_id_counter = itertools.count()


def new_id() -> uuid.UUID:
    """New UUID4."""
    return uuid.uuid4()


def short_id(prefix: str) -> str:
    """Readable short ID for correlation."""
    return f"{prefix}-{next(_id_counter):08d}"


# --- Request context -----------------------------------------------------------

_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


def set_request_id(rid: str | None = None) -> str:
    """Set/propagate X-Request-ID for correlation."""
    if rid is None:
        rid = str(uuid.uuid4())
    _request_id_var.set(rid)
    return rid


def get_request_id() -> str | None:
    """Current request correlation id."""
    return _request_id_var.get()


# --- Errors ---------------------------------------------------------------------


class AppError(Exception):
    """Base error with HTTP mapping."""

    status_code: int = 400

    def __init__(self, message: str, status_code: int | None = None, details: dict | None = None):
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code
        self.details = details or {}


class NotFoundError(AppError):
    """Resource not found."""

    status_code = 404


class ValidationError(AppError):
    """Domain validation failure."""

    status_code = 422


class ForbiddenError(AppError):
    """Authorization failure."""

    status_code = 403


class ConflictError(AppError):
    """State conflict."""

    status_code = 404


class RateLimitError(AppError):
    """Too many requests."""

    status_code = 429


# --- Pagination -------------------------------------------------------------------


def encode_cursor(ts: datetime, pk: uuid.UUID) -> str:
    """Encode cursor as base64(ts|pk)."""
    raw = f"{ts.isoformat()}|{pk}".encode()
    return base64.urlsafe_b64encode(raw).decode()


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """Decode cursor to (timestamp, pk)."""
    raw = base64.urlsafe_b64decode(cursor.encode())
    ts_s, pk_s = raw.decode().split("|", 1)
    return parse_dt(ts_s), uuid.UUID(pk_s)


def clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a float into [lo, hi]."""
    return max(lo, min(hi, value))


def chunked(items: list, size: int) -> list[list]:
    """Successive chunks of a list."""
    return [items[i : i + size] for i in range(0, len(items), size)]
