"""Person, consent, and enrollment repositories (spec §15)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, or_, select, text

from app.common.enums import ENROLLMENT_ACTIVE, ENROLLMENT_EXPIRED
from app.common.utils import utcnow
from app.models.persons import ConsentRecord, FaceEnrollment, PersonProfile
from app.repositories.base import BaseRepository, as_uuid


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity without numpy (portable fallback path)."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


class PersonRepository(BaseRepository):
    model = PersonProfile
    pk_attr = "person_id"
    order_attr = "created_at"

    async def create_person(
        self, display_name: str, access_role: str = "visitor", external_reference: str | None = None
    ) -> PersonProfile:
        person = PersonProfile(
            display_name=display_name,
            access_role=access_role,
            external_reference=external_reference,
            active=True,
        )
        self.add(person)
        await self.flush()
        return person

    async def list_persons(
        self, *, limit: int = 50, cursor: str | None = None, active_only: bool = False
    ):
        conditions = [PersonProfile.active.is_(True)] if active_only else None
        return await self.list_page(limit=limit, cursor=cursor, conditions=conditions)


class ConsentRepository(BaseRepository):
    model = ConsentRecord
    pk_attr = "consent_id"
    order_attr = "created_at"

    async def create_consent(
        self,
        person_id: uuid.UUID,
        purpose: str,
        allowed_camera_ids: list | None = None,
        allowed_zone_ids: list | None = None,
        valid_from: datetime | None = None,
        valid_until: datetime | None = None,
        evidence_reference: str | None = None,
    ) -> ConsentRecord:
        record = ConsentRecord(
            person_id=as_uuid(person_id),
            purpose=purpose,
            allowed_camera_ids=[str(c) for c in (allowed_camera_ids or [])] or None,
            allowed_zone_ids=[str(z) for z in (allowed_zone_ids or [])] or None,
            valid_from=valid_from or utcnow(),
            valid_until=valid_until,
            evidence_reference=evidence_reference,
        )
        self.add(record)
        await self.flush()
        return record

    async def active_consents_for_person(self, person_id: uuid.UUID, now: datetime | None = None):
        """Valid, non-revoked consents (spec §9 checks)."""
        now = now or utcnow()
        stmt = (
            select(ConsentRecord)
            .where(ConsentRecord.person_id == as_uuid(person_id))
            .where(ConsentRecord.revoked_at.is_(None))
            .where(ConsentRecord.valid_from <= now)
            .where(or_(ConsentRecord.valid_until.is_(None), ConsentRecord.valid_until > now))
            .order_by(ConsentRecord.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_by_person(self, person_id: uuid.UUID):
        stmt = (
            select(ConsentRecord)
            .where(ConsentRecord.person_id == as_uuid(person_id))
            .order_by(ConsentRecord.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def revoke(self, consent_id: uuid.UUID, when: datetime | None = None) -> int:
        record = await self.get(as_uuid(consent_id))
        if record is None or record.revoked_at is not None:
            return 0
        record.revoked_at = when or utcnow()
        await self.flush()
        return 1



class EnrollmentRepository(BaseRepository):
    model = FaceEnrollment
    pk_attr = "enrollment_id"
    order_attr = "created_at"

    async def create_enrollment(
        self,
        person_id: uuid.UUID,
        consent_id: uuid.UUID,
        embedding: list[float] | None,
        embedding_model_version: str = "hashing-v1",
        quality_metrics: dict | None = None,
        expires_at: datetime | None = None,
    ) -> FaceEnrollment:
        enrollment = FaceEnrollment(
            person_id=as_uuid(person_id),
            consent_id=as_uuid(consent_id),
            embedding=embedding,
            embedding_model_version=embedding_model_version,
            quality_metrics=quality_metrics,
            status=ENROLLMENT_ACTIVE,
            expires_at=expires_at,
        )
        self.add(enrollment)
        await self.flush()
        return enrollment

    async def list_active_for_person(self, person_id: uuid.UUID, now: datetime | None = None):
        """Active, non-expired enrollments (spec §9: usable only while valid)."""
        now = now or utcnow()
        stmt = (
            select(FaceEnrollment)
            .where(FaceEnrollment.person_id == as_uuid(person_id))
            .where(FaceEnrollment.status == ENROLLMENT_ACTIVE)
            .where(
                or_(
                    FaceEnrollment.expires_at.is_(None),
                    FaceEnrollment.expires_at > now,
                )
            )
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_all_for_person(self, person_id: uuid.UUID):
        stmt = select(FaceEnrollment).where(FaceEnrollment.person_id == as_uuid(person_id))
        return list((await self.session.execute(stmt)).scalars().all())

    async def delete_for_person(self, person_id: uuid.UUID) -> int:
        result = await self.session.execute(
            FaceEnrollment.__table__.delete().where(FaceEnrollment.person_id == as_uuid(person_id))
        )
        return result.rowcount or 0

    async def expire_outdated(self, now: datetime | None = None) -> int:
        """Mark expired enrollments (used by retention workers)."""
        now = now or utcnow()
        stmt = select(FaceEnrollment).where(
            and_(FaceEnrollment.status == ENROLLMENT_ACTIVE, FaceEnrollment.expires_at < now)
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        for row in rows:
            row.status = ENROLLMENT_EXPIRED
        await self.flush()
        return len(rows)

    async def search_similar(
        self, query: list[float], *, limit: int = 5
    ) -> list[tuple[FaceEnrollment, float]]:
        """Cosine gallery search (pgvector on PostgreSQL; in-memory fallback elsewhere)."""
        if self.session.bind is not None and self.session.bind.dialect.name == "postgresql":
            vec = "[" + ",".join(f"{x:.6f}" for x in query) + "]"
            sql = text(
                "SELECT enrollment_id, (embedding <=> CAST(:q AS vector)) AS dist "
                "FROM face_enrollments WHERE status = :status "
                "ORDER BY dist LIMIT :k"
            )
            result = await self.session.execute(
                sql, {"q": vec, "status": ENROLLMENT_ACTIVE, "k": limit}
            )
            out: list[tuple[FaceEnrollment, float]] = []
            for enrollment_id, dist in result.all():
                enrollment = await self.get(enrollment_id)
                if enrollment is not None:
                    out.append((enrollment, 1.0 - float(dist)))
            return out
        candidates = list(
            (
                await self.session.execute(
                    select(FaceEnrollment).where(FaceEnrollment.status == ENROLLMENT_ACTIVE)
                )
            )
            .scalars()
            .all()
        )
        scored = []
        for enrollment in candidates:
            if enrollment.embedding:
                scored.append((cosine(query, list(enrollment.embedding)), enrollment))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [(enrollment, score) for score, enrollment in scored[:limit]]
