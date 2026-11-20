"""Camera, zone, session, occupancy, and health repositories (spec §15)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, select

from app.common.enums import SESSION_ACTIVE, SESSION_CLOSED
from app.common.utils import utcnow
from app.models.ops import (
    CameraHealthEvent,
    CameraSource,
    CameraZone,
    OccupancySnapshot,
    VisitSession,
)
from app.repositories.base import BaseRepository, as_uuid


class CameraRepository(BaseRepository):
    model = CameraSource
    pk_attr = "camera_id"
    order_attr = "created_at"

    async def create_camera(
        self,
        name: str,
        stream_url_encrypted: str | None = None,
        location_label: str | None = None,
        enabled: bool = True,
    ) -> CameraSource:
        camera = CameraSource(
            name=name,
            stream_url_encrypted=stream_url_encrypted,
            location_label=location_label,
            enabled=enabled,
        )
        self.add(camera)
        await self.flush()
        return camera

    async def list_cameras(self, *, limit: int = 100, cursor: str | None = None):
        return await self.list_page(limit=limit, cursor=cursor)


class ZoneRepository(BaseRepository):
    model = CameraZone
    pk_attr = "zone_id"
    order_attr = "name"

    async def create_zone(
        self,
        camera_id: uuid.UUID,
        name: str,
        polygon: list | None,
        zone_type: str,
        access_policy: dict | None = None,
        max_occupancy: int | None = None,
        enabled: bool = True,
    ) -> CameraZone:
        zone = CameraZone(
            camera_id=as_uuid(camera_id),
            name=name,
            polygon=polygon,
            zone_type=zone_type,
            access_policy=access_policy,
            max_occupancy=max_occupancy,
            enabled=enabled,
        )
        self.add(zone)
        await self.flush()
        return zone

    async def list_zones(
        self, *, camera_id: uuid.UUID | None = None, limit: int = 100, cursor: str | None = None
    ):
        conditions = [CameraZone.camera_id == as_uuid(camera_id)] if camera_id else None
        return await self.list_page(limit=limit, cursor=cursor, conditions=conditions)

    async def zones_for_camera(self, camera_id: uuid.UUID) -> list[CameraZone]:
        stmt = select(CameraZone).where(CameraZone.camera_id == as_uuid(camera_id))
        return list((await self.session.execute(stmt)).scalars().all())


class SessionRepository(BaseRepository):
    model = VisitSession
    pk_attr = "session_id"
    order_attr = "started_at"

    async def get_active_known_session(
        self, person_id: uuid.UUID, camera_id: uuid.UUID, zone_id: uuid.UUID | None
    ):
        """Active session for person_id + camera_id + zone_id (spec §10)."""
        stmt = (
            select(VisitSession)
            .where(VisitSession.person_id == as_uuid(person_id))
            .where(VisitSession.camera_id == as_uuid(camera_id))
            .where(VisitSession.status == SESSION_ACTIVE)
            .where(
                VisitSession.zone_id == as_uuid(zone_id)
                if zone_id
                else VisitSession.zone_id.is_(None)
            )
            .order_by(VisitSession.started_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def get_active_anonymous_session(
        self, anonymous_subject_id: uuid.UUID, camera_id: uuid.UUID, zone_id: uuid.UUID | None
    ):
        stmt = (
            select(VisitSession)
            .where(VisitSession.anonymous_subject_id == as_uuid(anonymous_subject_id))
            .where(VisitSession.camera_id == as_uuid(camera_id))
            .where(VisitSession.status == SESSION_ACTIVE)
            .where(
                VisitSession.zone_id == as_uuid(zone_id)
                if zone_id
                else VisitSession.zone_id.is_(None)
            )
            .order_by(VisitSession.started_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def any_active_for_person_since(
        self, person_id: uuid.UUID, since: datetime
    ) -> VisitSession | None:
        """Any active session for the person started after ``since`` (session-gap rule)."""
        stmt = (
            select(VisitSession)
            .where(VisitSession.person_id == as_uuid(person_id))
            .where(VisitSession.status == SESSION_ACTIVE)
            .where(VisitSession.started_at >= since)
            .order_by(VisitSession.started_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def create_session(
        self,
        camera_id: uuid.UUID,
        track_id: uuid.UUID,
        person_id: uuid.UUID | None = None,
        anonymous_subject_id: uuid.UUID | None = None,
        zone_id: uuid.UUID | None = None,
        recognition_confidence: float | None = None,
        verification_status: str = "unverified",
        started_at: datetime | None = None,
    ) -> VisitSession:
        now = started_at or utcnow()
        session = VisitSession(
            person_id=as_uuid(person_id) if person_id else None,
            anonymous_subject_id=as_uuid(anonymous_subject_id) if anonymous_subject_id else None,
            camera_id=as_uuid(camera_id),
            zone_id=as_uuid(zone_id) if zone_id else None,
            track_id=as_uuid(track_id),
            status=SESSION_ACTIVE,
            started_at=now,
            last_seen_at=now,
            recognition_confidence=recognition_confidence,
            verification_status=verification_status,
        )
        self.add(session)
        await self.flush()
        return session

    async def close_session(
        self, session: VisitSession, when: datetime | None = None
    ) -> VisitSession:
        session.status = SESSION_CLOSED
        session.ended_at = when or utcnow()
        await self.flush()
        return session

    async def close_stale_sessions(
        self, absence_timeout_s: float, *, camera_id: uuid.UUID | None = None
    ) -> int:
        """Close sessions whose last_seen_at exceeds the absence timeout (spec §10)."""
        cutoff = utcnow() - timedelta(seconds=absence_timeout_s)
        stmt = select(VisitSession).where(
            VisitSession.status == SESSION_ACTIVE, VisitSession.last_seen_at < cutoff
        )
        if camera_id:
            stmt = stmt.where(VisitSession.camera_id == as_uuid(camera_id))
        stale = list((await self.session.execute(stmt)).scalars().all())
        for session in stale:
            session.status = SESSION_CLOSED
            session.ended_at = utcnow()
        await self.flush()
        return len(stale)

    async def list_sessions(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
        camera_id: uuid.UUID | None = None,
        person_id: uuid.UUID | None = None,
        status: str | None = None,
    ):
        conditions = []
        if camera_id:
            conditions.append(VisitSession.camera_id == as_uuid(camera_id))
        if person_id:
            conditions.append(VisitSession.person_id == as_uuid(person_id))
        if status:
            conditions.append(VisitSession.status == status)
        return await self.list_page(limit=limit, cursor=cursor, conditions=conditions or None)


class OccupancyRepository(BaseRepository):
    model = OccupancySnapshot
    pk_attr = "snapshot_id"
    order_attr = "timestamp"

    async def add_snapshot(
        self,
        camera_id: uuid.UUID,
        zone_id: uuid.UUID | None,
        occupancy_count: int,
        queue_count: int | None = None,
        estimated_wait_seconds: float | None = None,
        timestamp: datetime | None = None,
    ) -> OccupancySnapshot:
        snapshot = OccupancySnapshot(
            camera_id=as_uuid(camera_id),
            zone_id=as_uuid(zone_id) if zone_id else None,
            occupancy_count=occupancy_count,
            queue_count=queue_count,
            estimated_wait_seconds=estimated_wait_seconds,
            timestamp=timestamp or utcnow(),
        )
        self.add(snapshot)
        await self.flush()
        return snapshot

    async def latest_for_camera(self, camera_id: uuid.UUID) -> OccupancySnapshot | None:
        stmt = (
            select(OccupancySnapshot)
            .where(OccupancySnapshot.camera_id == as_uuid(camera_id))
            .order_by(OccupancySnapshot.timestamp.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def latest_for_zone(self, zone_id: uuid.UUID) -> OccupancySnapshot | None:
        stmt = (
            select(OccupancySnapshot)
            .where(OccupancySnapshot.zone_id == as_uuid(zone_id))
            .order_by(OccupancySnapshot.timestamp.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def aggregate(
        self,
        *,
        camera_id: uuid.UUID | None = None,
        zone_id: uuid.UUID | None = None,
        from_ts: datetime | None = None,
        to_ts: datetime | None = None,
    ) -> dict:
        """Aggregates for the occupancy report (spec §16)."""
        conditions = []
        if camera_id:
            conditions.append(OccupancySnapshot.camera_id == as_uuid(camera_id))
        if zone_id:
            conditions.append(OccupancySnapshot.zone_id == as_uuid(zone_id))
        if from_ts:
            conditions.append(OccupancySnapshot.timestamp >= from_ts)
        if to_ts:
            conditions.append(OccupancySnapshot.timestamp <= to_ts)
        stmt = select(
            func.count().label("samples"),
            func.max(OccupancySnapshot.occupancy_count).label("peak"),
            func.avg(OccupancySnapshot.occupancy_count).label("avg_occ"),
        )
        for cond in conditions:
            stmt = stmt.where(cond)
        row = (await self.session.execute(stmt)).one()
        return {
            "samples": int(row.samples or 0),
            "peak": int(row.peak or 0),
            "avg_occ": float(row.avg_occ or 0.0),
        }


class HealthRepository(BaseRepository):
    model = CameraHealthEvent
    pk_attr = "health_event_id"
    order_attr = "timestamp"

    async def add_event(
        self,
        camera_id: uuid.UUID,
        event_type: str,
        severity: str = "low",
        metrics: dict | None = None,
        timestamp: datetime | None = None,
    ) -> CameraHealthEvent:
        event = CameraHealthEvent(
            camera_id=as_uuid(camera_id),
            event_type=event_type,
            severity=severity,
            metrics=metrics,
            timestamp=timestamp or utcnow(),
        )
        self.add(event)
        await self.flush()
        return event

    async def open_incidents(self, camera_id: uuid.UUID | None = None):
        stmt = select(CameraHealthEvent).where(CameraHealthEvent.resolved_at.is_(None))
        if camera_id:
            stmt = stmt.where(CameraHealthEvent.camera_id == as_uuid(camera_id))
        stmt = stmt.order_by(CameraHealthEvent.timestamp.desc()).limit(200)
        return list((await self.session.execute(stmt)).scalars().all())

    async def resolve_open(self, camera_id: uuid.UUID, event_type: str) -> int:
        open_now = await self.open_incidents(camera_id)
        count = 0
        for event in open_now:
            if event.event_type == event_type:
                event.resolved_at = utcnow()
                count += 1
        await self.flush()
        return count

    async def report(
        self, *, from_ts: datetime | None = None, to_ts: datetime | None = None
    ) -> dict:
        conditions = []
        if from_ts:
            conditions.append(CameraHealthEvent.timestamp >= from_ts)
        if to_ts:
            conditions.append(CameraHealthEvent.timestamp <= to_ts)
        stmt = select(CameraHealthEvent)
        for cond in conditions:
            stmt = stmt.where(cond)
        rows = list((await self.session.execute(stmt)).scalars().all())
        by_type: dict[str, int] = {}
        by_camera: dict[str, int] = {}
        for row in rows:
            by_type[row.event_type] = by_type.get(row.event_type, 0) + 1
            key = str(row.camera_id)
            by_camera[key] = by_camera.get(key, 0) + 1
        return {"total": len(rows), "by_type": by_type, "by_camera": by_camera}
