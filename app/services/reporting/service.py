"""Reporting services for operational dashboards and exports."""
from __future__ import annotations
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.ops import OccupancyRepository, HealthRepository

class ReportingService:
    def __init__(self, session: AsyncSession) -> None:
        self.occupancy = OccupancyRepository(session)
        self.health = HealthRepository(session)

    async def occupancy_report(self, *, camera_id=None, zone_id=None, from_ts: datetime | None = None, to_ts: datetime | None = None) -> dict:
        data = await self.occupancy.aggregate(camera_id=camera_id, zone_id=zone_id, from_ts=from_ts, to_ts=to_ts)
        return {"camera_id": camera_id, "zone_id": zone_id, "from": from_ts, "to": to_ts, **data}

    async def health_report(self, *, from_ts: datetime | None = None, to_ts: datetime | None = None) -> dict:
        data = await self.health.report(from_ts=from_ts, to_ts=to_ts)
        return {"from": from_ts, "to": to_ts, **data}
