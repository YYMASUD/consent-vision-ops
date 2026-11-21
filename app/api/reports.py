from __future__ import annotations
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.deps import get_principal
from app.auth.security import Principal
from app.db.session import get_db
from app.services.reporting.service import ReportingService
router = APIRouter(prefix="/reports", tags=["reports"])
@router.get("/occupancy")
async def occupancy_report(camera_id: uuid.UUID | None = None, zone_id: uuid.UUID | None = None, from_ts: datetime | None = None, to_ts: datetime | None = None, db: AsyncSession = Depends(get_db), _: Principal = Depends(get_principal)):
    return await ReportingService(db).occupancy_report(camera_id=camera_id, zone_id=zone_id, from_ts=from_ts, to_ts=to_ts)
@router.get("/health")
async def health_report(from_ts: datetime | None = None, to_ts: datetime | None = None, db: AsyncSession = Depends(get_db), _: Principal = Depends(get_principal)):
    return await ReportingService(db).health_report(from_ts=from_ts, to_ts=to_ts)
