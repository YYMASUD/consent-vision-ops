"""Detection, recognition, access, and liveness event repositories (spec §15)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select

from app.common.utils import utcnow
from app.models.events import (
    AccessVerificationEvent,
    FaceDetection,
    LivenessEvent,
    RecognitionEvent,
)
from app.repositories.base import BaseRepository, as_uuid


class DetectionRepository(BaseRepository):
    model = FaceDetection
    pk_attr = "detection_id"
    order_attr = "timestamp"

    async def add_detection(
        self,
        camera_id: uuid.UUID,
        track_id: uuid.UUID,
        *,
        session_id: uuid.UUID | None = None,
        frame_number: int = 0,
        bbox: dict | None = None,
        confidence: float = 0.0,
        quality: dict | None = None,
        timestamp: datetime | None = None,
    ) -> FaceDetection:
        detection = FaceDetection(
            camera_id=as_uuid(camera_id),
            track_id=as_uuid(track_id),
            session_id=as_uuid(session_id) if session_id else None,
            frame_number=frame_number,
            bbox=bbox,
            confidence=confidence,
            quality=quality,
            timestamp=timestamp or utcnow(),
        )
        self.add(detection)
        await self.flush()
        return detection

    async def list_detections(
        self,
        *,
        limit: int = 100,
        cursor: str | None = None,
        camera_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
        track_id: uuid.UUID | None = None,
    ):
        conditions = []
        if camera_id:
            conditions.append(FaceDetection.camera_id == as_uuid(camera_id))
        if session_id:
            conditions.append(FaceDetection.session_id == as_uuid(session_id))
        if track_id:
            conditions.append(FaceDetection.track_id == as_uuid(track_id))
        return await self.list_page(limit=limit, cursor=cursor, conditions=conditions or None)


class RecognitionRepository(BaseRepository):
    model = RecognitionEvent
    pk_attr = "event_id"
    order_attr = "timestamp"

    async def add_event(
        self,
        decision: str,
        *,
        session_id: uuid.UUID | None = None,
        track_id: uuid.UUID | None = None,
        camera_id: uuid.UUID | None = None,
        zone_id: uuid.UUID | None = None,
        matched_person_id: uuid.UUID | None = None,
        similarity_score: float | None = None,
        threshold: float = 0.62,
        model_version: str = "hashing-v1",
        policy_status: str = "allowed",
        liveness_status: str | None = None,
        review_status: str = "none",
        timestamp: datetime | None = None,
    ) -> RecognitionEvent:
        event = RecognitionEvent(
            decision=decision,
            session_id=as_uuid(session_id) if session_id else None,
            track_id=as_uuid(track_id) if track_id else None,
            camera_id=as_uuid(camera_id) if camera_id else None,
            zone_id=as_uuid(zone_id) if zone_id else None,
            matched_person_id=as_uuid(matched_person_id) if matched_person_id else None,
            similarity_score=similarity_score,
            threshold=threshold,
            model_version=model_version,
            policy_status=policy_status,
            liveness_status=liveness_status,
            review_status=review_status,
            timestamp=timestamp or utcnow(),
        )
        self.add(event)
        await self.flush()
        return event

    async def list_events(
        self,
        *,
        limit: int = 100,
        cursor: str | None = None,
        camera_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
        person_id: uuid.UUID | None = None,
        decision: str | None = None,
    ):
        conditions = []
        if camera_id:
            conditions.append(RecognitionEvent.camera_id == as_uuid(camera_id))
        if session_id:
            conditions.append(RecognitionEvent.session_id == as_uuid(session_id))
        if person_id:
            conditions.append(RecognitionEvent.matched_person_id == as_uuid(person_id))
        if decision:
            conditions.append(RecognitionEvent.decision == decision)
        return await self.list_page(limit=limit, cursor=cursor, conditions=conditions or None)

    async def quality_counts(
        self, *, from_ts: datetime | None = None, to_ts: datetime | None = None
    ) -> dict:
        """Decision histogram for the recognition-quality report (spec §16)."""
        stmt = select(RecognitionEvent)
        if from_ts:
            stmt = stmt.where(RecognitionEvent.timestamp >= from_ts)
        if to_ts:
            stmt = stmt.where(RecognitionEvent.timestamp <= to_ts)
        rows = list((await self.session.execute(stmt)).scalars().all())
        by_decision: dict[str, int] = {}
        for row in rows:
            by_decision[row.decision] = by_decision.get(row.decision, 0) + 1


class AccessEventRepository(BaseRepository):
    model = AccessVerificationEvent
    pk_attr = "verification_id"
    order_attr = "timestamp"

    async def add_event(
        self,
        external_event_id: str,
        credential_type: str,
        *,
        credential_subject_reference: str | None = None,
        camera_id: uuid.UUID | None = None,
        zone_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
        decision: str = "granted",
        metadata: dict | None = None,
        timestamp: datetime | None = None,
    ) -> AccessVerificationEvent:
        event = AccessVerificationEvent(
            external_event_id=external_event_id,
            credential_type=credential_type,
            credential_subject_reference=credential_subject_reference,
            camera_id=as_uuid(camera_id) if camera_id else None,
            zone_id=as_uuid(zone_id) if zone_id else None,
            session_id=as_uuid(session_id) if session_id else None,
            decision=decision,
            extra_metadata=metadata,
            timestamp=timestamp or utcnow(),
        )
        self.add(event)
        await self.flush()
        return event

    async def list_events(
        self,
        *,
        limit: int = 100,
        cursor: str | None = None,
        camera_id: uuid.UUID | None = None,
        credential_type: str | None = None,
    ):
        conditions = []
        if camera_id:
            conditions.append(AccessVerificationEvent.camera_id == as_uuid(camera_id))
        if credential_type:
            conditions.append(AccessVerificationEvent.credential_type == credential_type)
        return await self.list_page(limit=limit, cursor=cursor, conditions=conditions or None)

    async def find_by_external_ids(self, external_event_ids: list[str]):
        if not external_event_ids:
            return []
        stmt = select(AccessVerificationEvent).where(
            AccessVerificationEvent.external_event_id.in_(external_event_ids)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def recent_for_subject(
        self, credential_subject_reference: str, since: datetime
    ) -> AccessVerificationEvent | None:
        """Most recent credential event for a subject (multi-factor correlation)."""
        stmt = (
            select(AccessVerificationEvent)
            .where(
                AccessVerificationEvent.credential_subject_reference == credential_subject_reference
            )
            .where(AccessVerificationEvent.timestamp >= since)
            .order_by(AccessVerificationEvent.timestamp.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalars().first()


class LivenessRepository(BaseRepository):
    model = LivenessEvent
    pk_attr = "liveness_event_id"
    order_attr = "timestamp"

    async def add_event(
        self,
        decision: str,
        *,
        track_id: uuid.UUID | None = None,
        camera_id: uuid.UUID | None = None,
        confidence: float | None = None,
        model_version: str = "heuristic-v1",
        metadata: dict | None = None,
        timestamp: datetime | None = None,
    ) -> LivenessEvent:
        event = LivenessEvent(
            decision=decision,
            track_id=as_uuid(track_id) if track_id else None,
            camera_id=as_uuid(camera_id) if camera_id else None,
            confidence=confidence,
            model_version=model_version,
            extra_metadata=metadata,
            timestamp=timestamp or utcnow(),
        )
        self.add(event)
        await self.flush()
        return event

    async def latest_for_track(self, track_id: uuid.UUID) -> LivenessEvent | None:
        stmt = (
            select(LivenessEvent)
            .where(LivenessEvent.track_id == as_uuid(track_id))
            .order_by(LivenessEvent.timestamp.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalars().first()
