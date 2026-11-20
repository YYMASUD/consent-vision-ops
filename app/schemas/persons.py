"""Pydantic v2 API schemas for persons, consent, and enrollment (spec §16)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Persons ------------------------------------------------------------------


class PersonCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)
    access_role: str = Field(default="visitor", max_length=64)
    external_reference: str | None = Field(default=None, max_length=200)


class PersonUpdate(BaseModel):
    display_name: str | None = None
    access_role: str | None = None
    active: bool | None = None


class PersonRead(ORMModel):
    person_id: uuid.UUID
    display_name: str
    access_role: str
    active: bool
    consent_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime | None = None


# --- Consent ------------------------------------------------------------------


class ConsentCreate(BaseModel):
    person_id: uuid.UUID
    purpose: str = Field(min_length=1, max_length=200)
    allowed_camera_ids: list[uuid.UUID] | None = None
    allowed_zone_ids: list[uuid.UUID] | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    evidence_reference: str | None = None


class ConsentRead(ORMModel):
    consent_id: uuid.UUID
    person_id: uuid.UUID
    purpose: str
    allowed_camera_ids: list | None = None
    allowed_zone_ids: list | None = None
    valid_from: datetime
    valid_until: datetime | None = None
    revoked_at: datetime | None = None
    evidence_reference: str | None = None
    created_at: datetime


class ConsentUpdate(BaseModel):
    valid_until: datetime | None = None
    purpose: str | None = None


# --- Enrollment ------------------------------------------------------------------


class EnrollmentCreate(BaseModel):
    person_id: uuid.UUID
    consent_id: uuid.UUID
    embedding: list[float] | None = None
    quality_metrics: dict | None = None
    embedding_model_version: str = "hashing-v1"
    expires_at: datetime | None = None


class EnrollmentRead(ORMModel):
    enrollment_id: uuid.UUID
    person_id: uuid.UUID
    consent_id: uuid.UUID
    embedding_model_version: str
    quality_metrics: dict | None = None
    status: str
    expires_at: datetime | None = None
    created_at: datetime


class EnrollImageRequest(BaseModel):
    """Enrollment from a raw still image; platform derives the embedding vector."""

    person_id: uuid.UUID
    consent_id: uuid.UUID
    image_b64: str = Field(min_length=16)
    expires_at: datetime | None = None


class DeleteBiometricResult(BaseModel):
    person_id: uuid.UUID
    enrollments_deleted: int
    consents_revoked: int
    audit_id: uuid.UUID | None = None