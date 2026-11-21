"""Retention service: sweeps expired biometric data and anonymous sessions."""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.models.governance import RetainedMedia, AuditLog
from app.models.ops import VisitSession, OccupancySnapshot
from app.models.persons import FaceEnrollment

logger = logging.getLogger(__name__)


class RetentionService:
    """Enforce data-retention policies per spec §19."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = get_settings()

    @classmethod
    async def run_sweep(cls, session: AsyncSession) -> dict[str, int]:
        """Run all retention sweeps and return counts of deleted rows."""
        svc = cls(session)
        counts: dict[str, int] = {}

        counts["anonymous_sessions"] = await svc._purge_anonymous_sessions()
        counts["expired_enrollments"] = await svc._purge_expired_enrollments()
        counts["expired_media"] = await svc._purge_expired_media()
        counts["old_occupancy"] = await svc._purge_old_occupancy_snapshots()

        logger.info("Retention sweep complete", extra={"counts": counts})
        return counts

    async def _purge_anonymous_sessions(self) -> int:
        """Delete anonymous visit sessions older than retention threshold."""
        cutoff = datetime.now(timezone.utc) - timedelta(
            hours=self._settings.anonymous_retention_hours
        )
        stmt = delete(VisitSession).where(
            VisitSession.person_id.is_(None),
            VisitSession.started_at < cutoff,
        )
        result = await self._session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

    async def _purge_expired_enrollments(self) -> int:
        """Delete face enrollments whose expires_at has passed."""
        now = datetime.now(timezone.utc)
        stmt = delete(FaceEnrollment).where(
            FaceEnrollment.expires_at.isnot(None),
            FaceEnrollment.expires_at < now,
        )
        result = await self._session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

    async def _purge_expired_media(self) -> int:
        """Delete retained_media records past their retention_expires_at."""
        now = datetime.now(timezone.utc)
        stmt = delete(RetainedMedia).where(
            RetainedMedia.retention_expires_at.isnot(None),
            RetainedMedia.retention_expires_at < now,
        )
        result = await self._session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]

    async def _purge_old_occupancy_snapshots(self) -> int:
        """Delete occupancy snapshots older than biometric_retention_days."""
        cutoff = datetime.now(timezone.utc) - timedelta(
            days=self._settings.biometric_retention_days
        )
        stmt = delete(OccupancySnapshot).where(OccupancySnapshot.timestamp < cutoff)
        result = await self._session.execute(stmt)
        return result.rowcount  # type: ignore[return-value]
