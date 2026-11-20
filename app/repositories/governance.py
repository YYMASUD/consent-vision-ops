"""Alert, review, retention, and audit repositories (spec §15)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select

from app.common.enums import ALERT_OPEN, CASE_OPEN
from app.common.utils import utcnow
from app.models.governance import (
    Alert,
    AlertRule,
    AuditLog,
    RetainedMedia,
    ReviewAction,
    ReviewCase,
)
from app.repositories.base import BaseRepository, as_uuid


class AlertRuleRepository(BaseRepository):
    model = AlertRule
    pk_attr = "rule_id"
    order_attr = "created_at"

    async def create_rule(
        self,
        name: str,
        condition: dict | None = None,
        severity: str = "medium",
        suppression_seconds: int = 600,
        escalation_policy: dict | None = None,
        enabled: bool = True,
    ) -> AlertRule:
        rule = AlertRule(
            name=name,
            condition=condition,
            severity=severity,
            suppression_seconds=suppression_seconds,
            escalation_policy=escalation_policy,
            enabled=enabled,
        )
        self.add(rule)
        await self.flush()
        return rule

    async def list_rules(self, *, limit: int = 100, cursor: str | None = None):
        return await self.list_page(limit=limit, cursor=cursor)

    async def enabled_rules(self) -> list[AlertRule]:
        stmt = select(AlertRule).where(AlertRule.enabled.is_(True))
        return list((await self.session.execute(stmt)).scalars().all())


class AlertRepository(BaseRepository):
    model = Alert
    pk_attr = "alert_id"
    order_attr = "created_at"

    async def find_by_dedup_key(self, dedup_key: str, since: datetime):
        """Existing alert inside the deduplication window (spec §13)."""
        stmt = (
            select(Alert)
            .where(Alert.deduplication_key == dedup_key)
            .where(Alert.created_at >= since)
            .order_by(Alert.created_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def create_alert(
        self,
        summary: str,
        *,
        severity: str = "medium",
        rule_id: uuid.UUID | None = None,
        camera_id: uuid.UUID | None = None,
        zone_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
        person_id: uuid.UUID | None = None,
        details: dict | None = None,
        deduplication_key: str | None = None,
    ) -> Alert:
        alert = Alert(
            summary=summary,
            severity=severity,
            status=ALERT_OPEN,
            rule_id=as_uuid(rule_id) if rule_id else None,
            camera_id=as_uuid(camera_id) if camera_id else None,
            zone_id=as_uuid(zone_id) if zone_id else None,
            session_id=as_uuid(session_id) if session_id else None,
            person_id=as_uuid(person_id) if person_id else None,
            details=details,
            deduplication_key=deduplication_key,
        )
        self.add(alert)
        await self.flush()
        return alert

    async def list_alerts(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
        status: str | None = None,
        severity: str | None = None,
        camera_id: uuid.UUID | None = None,
    ):
        conditions = []
        if status:
            conditions.append(Alert.status == status)
        if severity:
            conditions.append(Alert.severity == severity)
        if camera_id:
            conditions.append(Alert.camera_id == as_uuid(camera_id))
        return await self.list_page(limit=limit, cursor=cursor, conditions=conditions or None)


class ReviewRepository(BaseRepository):
    model = ReviewCase
    pk_attr = "review_case_id"
    order_attr = "opened_at"

    async def create_case(
        self,
        *,
        recognition_event_id: uuid.UUID | None = None,
        alert_id: uuid.UUID | None = None,
        priority: str = "medium",
        reason_code: str | None = None,
        assigned_to: str | None = None,
    ) -> ReviewCase:
        case = ReviewCase(
            recognition_event_id=as_uuid(recognition_event_id) if recognition_event_id else None,
            alert_id=as_uuid(alert_id) if alert_id else None,
            status=CASE_OPEN,
            priority=priority,
            reason_code=reason_code,
            assigned_to=assigned_to,
        )
        self.add(case)
        await self.flush()
        return case

    async def list_cases(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
        status: str | None = None,
        assigned_to: str | None = None,
    ):
        conditions = []
        if status:
            conditions.append(ReviewCase.status == status)
        if assigned_to:
            conditions.append(ReviewCase.assigned_to == assigned_to)
        return await self.list_page(limit=limit, cursor=cursor, conditions=conditions or None)

    async def add_action(
        self,
        review_case_id: uuid.UUID,
        reviewer_id: str,
        action: str,
        *,
        prior_decision: str | None = None,
        new_decision: str | None = None,
        reason_code: str | None = None,
        notes: str | None = None,
    ) -> ReviewAction:
        record = ReviewAction(
            review_case_id=as_uuid(review_case_id),
            reviewer_id=reviewer_id,
            action=action,
            prior_decision=prior_decision,
            new_decision=new_decision,
            reason_code=reason_code,
            notes=notes,
        )
        self.add(record)
        await self.flush()
        return record

    async def actions_for_case(self, review_case_id: uuid.UUID):
        stmt = (
            select(ReviewAction)
            .where(ReviewAction.review_case_id == as_uuid(review_case_id))
            .order_by(ReviewAction.created_at.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())


class RetentionRepository(BaseRepository):
    model = RetainedMedia
    pk_attr = "media_id"
    order_attr = "created_at"

    async def add_media(
        self,
        storage_key: str,
        *,
        session_id: uuid.UUID | None = None,
        media_type: str = "image",
        encrypted: bool = False,
        retention_expires_at: datetime | None = None,
        approved_by: str | None = None,
    ) -> RetainedMedia:
        media = RetainedMedia(
            storage_key=storage_key,
            session_id=as_uuid(session_id) if session_id else None,
            media_type=media_type,
            encrypted=encrypted,
            retention_expires_at=retention_expires_at,
            approved_by=approved_by,
        )
        self.add(media)
        await self.flush()
        return media

    async def expired_media(self, now: datetime | None = None, limit: int = 500):
        now = now or utcnow()
        stmt = (
            select(RetainedMedia)
            .where(RetainedMedia.retention_expires_at.is_not(None))
            .where(RetainedMedia.retention_expires_at < now)
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())


class AuditRepository(BaseRepository):
    model = AuditLog
    pk_attr = "audit_id"
    order_attr = "timestamp"

    async def record(
        self,
        action: str,
        resource_type: str,
        *,
        actor_id: str | None = None,
        resource_id: str | None = None,
        request_id: str | None = None,
        outcome: str = "success",
        metadata: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            action=action,
            resource_type=resource_type,
            actor_id=actor_id,
            resource_id=resource_id,
            request_id=request_id,
            outcome=outcome,
            extra_metadata=metadata,
        )
        self.add(entry)
        await self.flush()
        return entry

    async def list_logs(
        self,
        *,
        limit: int = 100,
        cursor: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        actor_id: str | None = None,
    ):
        conditions = []
        if action:
            conditions.append(AuditLog.action == action)
        if resource_type:
            conditions.append(AuditLog.resource_type == resource_type)
        if actor_id:
            conditions.append(AuditLog.actor_id == actor_id)
        return await self.list_page(limit=limit, cursor=cursor, conditions=conditions or None)