"""Alerts, review workflow, retention, and audit ORM models (spec §15)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import ALERT_OPEN, CASE_OPEN
from app.common.utils import utcnow
from app.models.base import Base, JSONType, UUIDPk


class AlertRule(Base):
    """Configurable alert rule evaluated against event streams."""

    __tablename__ = "alert_rules"

    rule_id: Mapped[uuid.UUID] = mapped_column(UUIDPk, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    condition: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    severity: Mapped[str] = mapped_column(String(32), default="medium")
    suppression_seconds: Mapped[int] = mapped_column(default=600)
    escalation_policy: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Alert(Base):
    """Raised alert incident."""

    __tablename__ = "alerts"

    alert_id: Mapped[uuid.UUID] = mapped_column(UUIDPk, primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("alert_rules.rule_id"), nullable=True
    )
    severity: Mapped[str] = mapped_column(String(32), default="medium")
    status: Mapped[str] = mapped_column(String(32), default=ALERT_OPEN)
    camera_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPk, nullable=True)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPk, nullable=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPk, nullable=True)
    person_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPk, nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    details: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    deduplication_key: Mapped[str | None] = mapped_column(String(200), index=True, nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String(200), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReviewCase(Base):
    """Human-review case for uncertain or conflicting decisions."""

    __tablename__ = "review_cases"

    review_case_id: Mapped[uuid.UUID] = mapped_column(UUIDPk, primary_key=True, default=uuid.uuid4)
    recognition_event_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPk, nullable=True)
    alert_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPk, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=CASE_OPEN)
    priority: Mapped[str] = mapped_column(String(32), default="medium")
    assigned_to: Mapped[str | None] = mapped_column(String(200), nullable=True)
    decision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(200), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReviewAction(Base):
    """Immutable action trail for a review case."""

    __tablename__ = "review_actions"

    review_action_id: Mapped[uuid.UUID] = mapped_column(UUIDPk, primary_key=True, default=uuid.uuid4)
    review_case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("review_cases.review_case_id"))
    reviewer_id: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(64))
    prior_decision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_decision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RetainedMedia(Base):
    """Reference to retained media subject to retention policy."""

    __tablename__ = "retained_media"

    media_id: Mapped[uuid.UUID] = mapped_column(UUIDPk, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPk, nullable=True)
    storage_key: Mapped[str] = mapped_column(Text)
    media_type: Mapped[str] = mapped_column(String(50), default="image")
    encrypted: Mapped[bool] = mapped_column(Boolean, default=False)
    retention_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    """Immutable audit trail for sensitive actions."""

    __tablename__ = "audit_logs"

    audit_id: Mapped[uuid.UUID] = mapped_column(UUIDPk, primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    resource_type: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    outcome: Mapped[str] = mapped_column(String(32), default="success")
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSONType, nullable=True)
