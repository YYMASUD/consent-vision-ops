"""Shared ORM column types: portable UUID PKs, JSON columns, embedding vectors."""
from __future__ import annotations

import uuid

from sqlalchemy import CHAR, JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.types import TypeDecorator

# Re-export the shared declarative base so model modules import from one place.
from app.db.session import Base  # noqa: F401

EMBED_DIM = 512


class UUIDPk(TypeDecorator):
    """Portable GUID: native UUID on PostgreSQL, CHAR(36) elsewhere."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):  # noqa: ANN001, ANN201
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PGUUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):  # noqa: ANN001, ANN201
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value, dialect):  # noqa: ANN001, ANN201
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return uuid.UUID(str(value))


class JSONType(TypeDecorator):
    """JSONB on PostgreSQL, JSON elsewhere."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):  # noqa: ANN001, ANN201
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return super().load_dialect_impl(dialect)


class EmbeddingVector(TypeDecorator):
    """pgvector Vector on PostgreSQL; JSON float list elsewhere (dev/test)."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):  # noqa: ANN001, ANN201
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector

            return dialect.type_descriptor(Vector(EMBED_DIM))
        return super().load_dialect_impl(dialect)

    def process_bind_param(self, value, dialect):  # noqa: ANN001, ANN201
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return [float(x) for x in value]

    def process_result_value(self, value, dialect):  # noqa: ANN001, ANN201
        if value is None:
            return None
        return [float(x) for x in value]


__all__ = ["Base", "UUIDPk", "JSONType", "EmbeddingVector", "EMBED_DIM"]