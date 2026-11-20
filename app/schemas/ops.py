"""Pydantic v2 API schemas for cameras, zones, sessions, occupancy, health."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.persons import ORMModel


# --- Cameras ------------------------------------------------------------------


class CameraCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    stream_url: str | None = None
    location_label: str | None = None
    enabled: bool = True


class CameraUpdate(BaseModel):
    name: str | None = None
    stream_url: str | None = None
    location_label: str | None = None
    enabled: bool | None = None


class CameraRead(ORMModel):
    camera_id: uuid.UUID
    name: str
    enabled: bool
    location_label: str | None = None
    health_status: str
    created_at: datetime
    updated_at: datetime


# --- Zones ------------------------------------------------------------------


class ZoneCreate(BaseModel):
    camera_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    polygon: list[list[float]] | None = None
    zone_type: str = "service_zone"
    access_policy: dict | None = None
    max_occupancy: int | None = None
    enabled: bool = True


class ZoneUpdate(BaseModel):
    name: str | None = None
    polygon: list[list[float]] | None = None
    zone_type: str | None = None
    access_policy: dict | None = None
    max_occupancy: int | None = None
    enabled: bool | None = None


class ZoneRead(ORMModel):
    zone_id: uuid.UUID
    camera_id: uuid.UUID
    name: str
    polygon: list | None = None
    zone_type: str
    access_policy: dict | None = None
    max_occupancy: int | None = None
    enabled: bool


# --- Sessions ------------------------------------------------------------------


class SessionRead(ORMModel):
    session_id: uuid.UUID
    person_id: uuid.UUID | None = None
    anonymous_subject_id: uuid.UUID | None = None
    camera_id: uuid.UUID
    zone_id: uuid.UUID | None = None
    track_id: uuid.UUID
    status: str
    started_at: datetime
    last_seen_at: datetime
    ended_at: datetime | None = None
    recognition_confidence: float | None = None
    verification_status: str


class SessionCloseResult(BaseModel):
    session_id: uuid.UUID
    status: str
    ended_at: datetime


# --- Occupancy / queue ------------------------------------------------------------------


class OccupancySnapshotRead(ORMModel):
    snapshot_id: uuid.UUID
    camera_id: uuid.UUID
    zone_id: uuid.UUID | None = None
    timestamp: datetime
    occupancy_count: int
    queue_count: int | None = None
    estimated_wait_seconds: float | None = None


class ZoneOccupancy(BaseModel):
    zone_id: uuid.UUID | None
    camera_id: uuid.UUID
    occupancy_count: int
    max_occupancy: int | None = None
    updated_at: datetime | None = None


class QueueMetrics(BaseModel):
    camera_id: uuid.UUID | None = None
    zone_id: uuid.UUID | None = None
    queue_count: int = 0
    estimated_wait_seconds: float = 0.0


# --- Camera health ------------------------------------------------------------------


class CameraHealthRead(ORMModel):
    health_event_id: uuid.UUID
    camera_id: uuid.UUID
    timestamp: datetime
    event_type: str
    severity: str
    metrics: dict | None = None
    resolved_at: datetime | None = None


class CameraHealthSummary(BaseModel):
    camera_id: uuid.UUID
    health_status: str
    fps: float = 0.0
    last_frame_at: datetime | None = None
    reconnects: int = 0
    decode_errors: int = 0
    open_incidents: int = 0