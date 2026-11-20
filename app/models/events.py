"""Detection, recognition, access, and liveness event ORM models (spec §15)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.utils import utcnow
from app.models.base import Base, JSONType, UUIDPk


class FaceDetection(Base):
    """Observed face within a frame, tied to a track."""

    __tablename__ = "face_detections"

    detection_id: Mapped[uuid.UUID] = mapped_column(UUIDPk, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("visit_sessions.session_id"), nullable=True
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(UUIDPk)
    track_id: Mapped[uuid.UUID] = mapped_column(UUIDPk)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    frame_number: Mapped[int] = mapped_column(default=0)
    bbox: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    quality: Mapped[dict | None] = mapped_column(JSONType, nullable=True)


class RecognitionEvent(Base):
    """One recognition decision (individual, auditable)."""

    __tablename__ = "recognition_events"

    event_id: Mapped[uuid.UUID] = mapped_column(UUIDPk, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("visit_sessions.session_id"), nullable=True
    )
    track_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPk, nullable=True)
    camera_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPk, nullable=True)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPk, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decision: Mapped[str] = mapped_column(String(64))
    matched_person_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPk, nullable=True)
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold: Mapped[float] = mapped_column(Float, default=0.62)
    model_version: Mapped[str] = mapped_column(String(64), default="hashing-v1")
    policy_status: Mapped[str] = mapped_column(String(64), default="allowed")
    liveness_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    review_status: Mapped[str] = mapped_column(String(64), default="none")


class AccessVerificationEvent(Base):
    """External access-control evidence (badge/QR/NFC/PIN/turnstile/door/manual)."""

    __tablename__ = "access_verification_events"

    verification_id: Mapped[uuid.UUID] = mapped_column(UUIDPk, primary_key=True, default=uuid.uuid4)
    camera_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPk, nullable=True)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPk, nullable=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPk, nullable=True)
    external_event_id: Mapped[str] = mapped_column(String(200))
    credential_type: Mapped[str] = mapped_column(String(50))
    credential_subject_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    decision: Mapped[str] = mapped_column(String(50))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSONType, nullable=True)


class LivenessEvent(Base):
    """Anti-spoofing assessment outcome."""

    __tablename__ = "liveness_events"

    liveness_event_id: Mapped[uuid.UUID] = mapped_column(UUIDPk, primary_key=True, default=uuid.uuid4)
    track_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPk, nullable=True)
    camera_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPk, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decision: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_version: Mapped[str] = mapped_column(String(64), default="heuristic-v1")
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSONType, nullable=True)
