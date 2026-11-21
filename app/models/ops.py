"""Cameras, zones, sessions, occupancy, and health ORM models (spec §15)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import CAM_UNKNOWN, SESSION_ACTIVE, VERIFICATION_UNVERIFIED
from app.common.utils import utcnow
from app.models.base import Base, JSONType, UUIDPk


class CameraSource(Base):
    """Registered camera/stream source."""

    __tablename__ = "camera_sources"

    camera_id: Mapped[uuid.UUID] = mapped_column(UUIDPk, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    stream_url_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    location_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    health_status: Mapped[str] = mapped_column(String(32), default=CAM_UNKNOWN)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CameraZone(Base):
    """Polygon zone attached to one camera."""

    __tablename__ = "camera_zones"

    zone_id: Mapped[uuid.UUID] = mapped_column(UUIDPk, primary_key=True, default=uuid.uuid4)
    camera_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("camera_sources.camera_id"))
    name: Mapped[str] = mapped_column(String(200))
    polygon: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    zone_type: Mapped[str] = mapped_column(String(50))
    access_policy: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    max_occupancy: Mapped[int | None] = mapped_column(nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class VisitSession(Base):
    """One physical visit to a camera/zone — known or anonymous."""

    __tablename__ = "visit_sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(UUIDPk, primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("person_profiles.person_id"), nullable=True
    )
    anonymous_subject_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPk, nullable=True)
    camera_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("camera_sources.camera_id"))
    zone_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("camera_zones.zone_id"), nullable=True
    )
    track_id: Mapped[uuid.UUID] = mapped_column(UUIDPk)
    status: Mapped[str] = mapped_column(String(32), default=SESSION_ACTIVE)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recognition_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(32), default=VERIFICATION_UNVERIFIED)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class OccupancySnapshot(Base):
    """Privacy-preserving occupancy sample (no identity required)."""

    __tablename__ = "occupancy_snapshots"

    snapshot_id: Mapped[uuid.UUID] = mapped_column(UUIDPk, primary_key=True, default=uuid.uuid4)
    camera_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("camera_sources.camera_id"))
    zone_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("camera_zones.zone_id"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    occupancy_count: Mapped[int] = mapped_column(default=0)
    queue_count: Mapped[int | None] = mapped_column(nullable=True)
    estimated_wait_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)


class CameraHealthEvent(Base):
    """Stream/camera health observation or incident."""

    __tablename__ = "camera_health_events"

    health_event_id: Mapped[uuid.UUID] = mapped_column(UUIDPk, primary_key=True, default=uuid.uuid4)
    camera_id: Mapped[uuid.UUID] = mapped_column(UUIDPk)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    event_type: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(32), default="low")
    metrics: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
