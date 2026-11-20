"""Persons, consent records, and face enrollments ORM models (spec §15)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import ENROLLMENT_ACTIVE
from app.common.utils import utcnow
from app.models.base import Base, EmbeddingVector, JSONType, UUIDPk


class PersonProfile(Base):
    """Persistent identity profile. Created ONLY via explicit enrollment."""

    __tablename__ = "person_profiles"

    person_id: Mapped[uuid.UUID] = mapped_column(UUIDPk, primary_key=True, default=uuid.uuid4)
    display_name: Mapped[str] = mapped_column(String(200))
    access_role: Mapped[str] = mapped_column(String(64), default="visitor")
    external_reference: Mapped[str | None] = mapped_column(
        String(200), nullable=True, unique=False, index=True
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    consent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("consent_records.consent_id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ConsentRecord(Base):
    """Documented consent granting biometric recognition under a legal basis."""

    __tablename__ = "consent_records"

    consent_id: Mapped[uuid.UUID] = mapped_column(UUIDPk, primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("person_profiles.person_id"))
    purpose: Mapped[str] = mapped_column(String(200))
    allowed_camera_ids: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    allowed_zone_ids: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FaceEnrollment(Base):
    """Persistent biometric enrollment tied to an active consent."""

    __tablename__ = "face_enrollments"

    enrollment_id: Mapped[uuid.UUID] = mapped_column(UUIDPk, primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("person_profiles.person_id"))
    consent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consent_records.consent_id"))
    embedding: Mapped[list | None] = mapped_column(EmbeddingVector, nullable=True)
    embedding_model_version: Mapped[str] = mapped_column(String(64), default="hashing-v1")
    quality_metrics: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=ENROLLMENT_ACTIVE)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)