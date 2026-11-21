"""Camera health monitoring service."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ops import CameraHealthEvent, CameraSource
from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class CameraHealthService:
    """Check camera health and persist health events (spec §16)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = get_settings()

    @classmethod
    async def check_and_persist(cls, session: AsyncSession, camera: CameraSource) -> CameraHealthEvent | None:
        """
        Run a lightweight health heuristic against a camera record and persist
        a health event if an issue is detected. Returns the persisted event or
        None when the camera appears healthy.
        """
        svc = cls(session)
        return await svc._evaluate(camera)

    async def _evaluate(self, camera: CameraSource) -> CameraHealthEvent | None:
        """
        Evaluate the camera's current status field and emit a health event when
        status is not 'online'. In production this would inspect actual stream
        metrics; here we use the persisted health_status as the signal.
        """
        HEALTHY_STATUSES = {"online", "unknown"}
        status = (camera.health_status or "unknown").lower()

        if status in HEALTHY_STATUSES:
            return None

        event_type_map = {
            "offline": "camera_offline",
            "degraded": "stream_degraded",
            "frozen": "frozen_frame",
            "black": "black_screen",
            "obstructed": "lens_obstruction",
        }
        event_type = event_type_map.get(status, "health_check_failed")
        severity = "high" if status == "offline" else "medium"

        event = CameraHealthEvent(
            health_event_id=uuid.uuid4(),
            camera_id=camera.camera_id,
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            severity=severity,
            metrics={"health_status": status},
        )
        session = self._session
        session.add(event)
        await session.flush()
        logger.warning(
            "Camera health event persisted",
            extra={
                "camera_id": str(camera.camera_id),
                "event_type": event_type,
                "severity": severity,
            },
        )
        return event
