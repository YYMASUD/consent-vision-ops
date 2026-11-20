"""Pydantic v2 API schemas for detections, recognition, access, liveness events."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.persons import ORMModel


class DetectionRead(ORMModel):
    detection_id: uuid.UUID
    session_id: uuid.UUID | None = None
    camera_id: uuid.UUID
    track_id: uuid.UUID
    timestamp: datetime
    frame_number: int
    bbox: dict | None = None
    confidence: float
    quality: dict | None = None


class RecognitionEventRead(ORMModel):
    event_id: uuid.UUID
    session_id: uuid.UUID | None = None
    track_id: uuid.UUID | None = None
    camera_id: uuid.UUID | None = None
    zone_id: uuid.UUID | None = None
    timestamp: datetime
    decision: str
    matched_person_id: uuid.UUID | None = None
    similarity_score: float | None = None
    threshold: float
    model_version: str
    policy_status: str
    liveness_status: str | None = None
    review_status: str


class AccessEventCreate(BaseModel):
    external_event_id: str = Field(min_length=1, max_length=200)
    credential_type: str = Field(min_length=1, max_length=50)
    credential_subject_reference: str | None = Field(default=None, max_length=200)
    camera_id: uuid.UUID | None = None
    zone_id: uuid.UUID | None = None
    decision: str = "granted"
    metadata: dict | None = None


class AccessEventRead(ORMModel):
    verification_id: uuid.UUID
    camera_id: uuid.UUID | None = None
    zone_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    external_event_id: str
    credential_type: str
    credential_subject_reference: str | None = None
    decision: str
    timestamp: datetime
    metadata: dict | None = None


class AccessReplayRequest(BaseModel):
    external_event_ids: list[str] = Field(min_length=1)


class LivenessEventRead(ORMModel):
    liveness_event_id: uuid.UUID
    track_id: uuid.UUID | None = None
    camera_id: uuid.UUID | None = None
    timestamp: datetime
    decision: str
    confidence: float | None = None
    model_version: str
    metadata: dict | None = None


class LiveTrack(BaseModel):
    track_id: uuid.UUID
    camera_id: uuid.UUID
    state: str
    zone_id: uuid.UUID | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    person_id: uuid.UUID | None = None
    is_anonymous: bool = True