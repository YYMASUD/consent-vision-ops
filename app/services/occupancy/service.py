"""Occupancy snapshot service: count and persist zone occupancy samples."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ops import CameraSource, CameraZone, OccupancySnapshot, VisitSession
from app.common.enums import SESSION_ACTIVE

logger = logging.getLogger(__name__)

SESSION_ACTIVE_STR = SESSION_ACTIVE if isinstance(SESSION_ACTIVE, str) else SESSION_ACTIVE.value  # type: ignore[union-attr]


class OccupancyService:
    """Compute and persist privacy-preserving occupancy snapshots (spec §18)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @classmethod
    async def snapshot(cls, session: AsyncSession, camera: CameraSource) -> list[OccupancySnapshot]:
        """
        Count active sessions per zone for the given camera and persist
        OccupancySnapshot rows. Returns list of persisted snapshots.
        """
        svc = cls(session)
        return await svc._take_snapshot(camera)

    async def _take_snapshot(self, camera: CameraSource) -> list[OccupancySnapshot]:
        """Aggregate active session counts by zone and camera, write snapshots."""
        snapshots: list[OccupancySnapshot] = []
        now = datetime.now(timezone.utc)

        # Count sessions without zone assignment (whole-camera occupancy)
        camera_count_stmt = select(VisitSession).where(
            VisitSession.camera_id == camera.camera_id,
            VisitSession.status == SESSION_ACTIVE_STR,
        )
        result = await self._session.execute(camera_count_stmt)
        active_sessions = result.scalars().all()

        # Group by zone_id
        zone_counts: dict[uuid.UUID | None, int] = {}
        for session_row in active_sessions:
            zone_counts[session_row.zone_id] = zone_counts.get(session_row.zone_id, 0) + 1

        # Ensure we always emit a whole-camera snapshot
        if not zone_counts:
            zone_counts[None] = 0

        for zone_id, count in zone_counts.items():
            snap = OccupancySnapshot(
                snapshot_id=uuid.uuid4(),
                camera_id=camera.camera_id,
                zone_id=zone_id,
                timestamp=now,
                occupancy_count=count,
            )
            self._session.add(snap)
            snapshots.append(snap)

        if snapshots:
            await self._session.flush()
            logger.debug(
                "Occupancy snapshots written",
                extra={"camera_id": str(camera.camera_id), "zones": len(snapshots)},
            )

        return snapshots
