"""Pydantic v2 API schemas for alerts, reviews, retention, reports (spec §16)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.persons import ORMModel


# --- Alert rules ------------------------------------------------------------------


class AlertRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    condition: dict | None = None
    severity: str = "medium"
    suppression_seconds: int = 600
    escalation_policy: dict | None = None
    enabled: bool = True


class AlertRuleUpdate(BaseModel):
    name: str | None = None
    condition: dict | None = None
    severity: str | None = None
    suppression_seconds: int | None = None
    escalation_policy: dict | None = None
    enabled: bool | None = None


class AlertRuleRead(ORMModel):
    rule_id: uuid.UUID
    name: str
    enabled: bool
    condition: dict | None = None
    severity: str
    suppression_seconds: int
    escalation_policy: dict | None = None
    created_at: datetime
    updated_at: datetime


# --- Alerts ------------------------------------------------------------------


class AlertRead(ORMModel):
    alert_id: uuid.UUID
    rule_id: uuid.UUID | None = None
    severity: str
    status: str
    camera_id: uuid.UUID | None = None
    zone_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    person_id: uuid.UUID | None = None
    summary: str
    details: dict | None = None
    deduplication_key: str | None = None
    assigned_to: str | None = None
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    created_at: datetime


class AlertAssignRequest(BaseModel):
    assigned_to: str = Field(min_length=1, max_length=200)


class AlertAckRequest(BaseModel):
    acknowledged_by: str | None = None


class AlertResolveRequest(BaseModel):
    resolved_by: str | None = None
    notes: str | None = None


# --- Reviews ------------------------------------------------------------------


class ReviewCaseRead(ORMModel):
    review_case_id: uuid.UUID
    recognition_event_id: uuid.UUID | None = None
    alert_id: uuid.UUID | None = None
    status: str
    priority: str
    assigned_to: str | None = None
    decision: str | None = None
    reason_code: str | None = None
    opened_at: datetime
    closed_at: datetime | None = None


class ReviewActionRequest(BaseModel):
    reviewer_id: str = Field(min_length=1, max_length=200)
    action: str = Field(min_length=1, max_length=64)
    reason_code: str | None = Field(default=None, max_length=200)
    notes: str | None = None


class ReviewActionRead(ORMModel):
    review_action_id: uuid.UUID
    review_case_id: uuid.UUID
    reviewer_id: str
    action: str
    prior_decision: str | None = None
    new_decision: str | None = None
    reason_code: str | None = None
    notes: str | None = None
    created_at: datetime


# --- Retention ------------------------------------------------------------------


class RetentionRunResult(BaseModel):
    ran_at: datetime
    media_deleted: int
    anonymous_sessions_deleted: int
    liveness_metadata_deleted: int
    detections_deleted: int
    enrollments_expired: int


class RetentionStatus(BaseModel):
    last_run_at: datetime | None = None
    last_result: RetentionRunResult | None = None
    anonymous_retention_hours: float
    biometric_retention_days: int


# --- Reports ------------------------------------------------------------------


class OccupancyReport(BaseModel):
    camera_id: uuid.UUID | None = None
    zone_id: uuid.UUID | None = None
    from_ts: datetime | None = None
    to_ts: datetime | None = None
    peak_occupancy: int = 0
    average_occupancy: float = 0.0
    average_dwell_seconds: float = 0.0
    total_sessions: int = 0
    anonymous_sessions: int = 0
    samples: int = 0


class QueueReport(BaseModel):
    camera_id: uuid.UUID | None = None
    zone_id: uuid.UUID | None = None
    average_queue_count: float = 0.0
    peak_queue_count: int = 0
    average_wait_seconds: float = 0.0
    samples: int = 0


class CameraHealthReport(BaseModel):
    from_ts: datetime | None = None
    to_ts: datetime | None = None
    incidents_total: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
    by_camera: dict[str, int] = Field(default_factory=dict)


class RecognitionQualityReport(BaseModel):
    from_ts: datetime | None = None
    to_ts: datetime | None = None
    total_decisions: int = 0
    by_decision: dict[str, int] = Field(default_factory=dict)
    confirmed_rate: float = 0.0
    uncertain_rate: float = 0.0
    false_match_review_rate: float = 0.0
    false_nonmatch_review_rate: float = 0.0


# --- Audit ------------------------------------------------------------------


class AuditLogRead(ORMModel):
    audit_id: uuid.UUID
    actor_id: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    request_id: str | None = None
    timestamp: datetime
    outcome: str
    metadata: dict | None = None