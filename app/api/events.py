"""Operational event and dashboard endpoints."""
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.deps import get_principal
from app.auth.security import Principal
from app.db.session import get_db
from app.repositories.events import DetectionRepository, RecognitionRepository, AccessEventRepository
from app.schemas.common import Page
from app.schemas.events import DetectionRead, RecognitionEventRead, AccessEventCreate, AccessEventRead, LiveTrack

router = APIRouter(tags=["events"])

def _page(items, cursor, converter):
    return Page(items=[converter.model_validate(x) for x in items], next_cursor=cursor)

@router.get("/detections", response_model=Page[DetectionRead])
async def detections(limit: int = 100, cursor: str | None = None, camera_id: uuid.UUID | None = None, session_id: uuid.UUID | None = None, track_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_db), _: Principal = Depends(get_principal)):
    rows, nxt = await DetectionRepository(db).list_detections(limit=limit, cursor=cursor, camera_id=camera_id, session_id=session_id, track_id=track_id)
    return _page(rows, nxt, DetectionRead)

@router.get("/recognition-events", response_model=Page[RecognitionEventRead])
async def recognition_events(limit: int = 100, cursor: str | None = None, camera_id: uuid.UUID | None = None, decision: str | None = None, db: AsyncSession = Depends(get_db), _: Principal = Depends(get_principal)):
    rows, nxt = await RecognitionRepository(db).list_events(limit=limit, cursor=cursor, camera_id=camera_id, decision=decision)
    return _page(rows, nxt, RecognitionEventRead)

@router.get("/access-events", response_model=Page[AccessEventRead])
async def access_events(limit: int = 100, cursor: str | None = None, camera_id: uuid.UUID | None = None, credential_type: str | None = None, db: AsyncSession = Depends(get_db), _: Principal = Depends(get_principal)):
    rows, nxt = await AccessEventRepository(db).list_events(limit=limit, cursor=cursor, camera_id=camera_id, credential_type=credential_type)
    return _page(rows, nxt, AccessEventRead)

@router.post("/access-events", response_model=AccessEventRead, status_code=201)
async def create_access_event(body: AccessEventCreate, db: AsyncSession = Depends(get_db), _: Principal = Depends(get_principal)):
    row = await AccessEventRepository(db).add_event(body.external_event_id, body.credential_type, credential_subject_reference=body.credential_subject_reference, camera_id=body.camera_id, zone_id=body.zone_id, decision=body.decision, metadata=body.metadata)
    return AccessEventRead.model_validate(row)

@router.get("/live-tracks", response_model=list[LiveTrack])
async def live_tracks(_: Principal = Depends(get_principal)):
    return []

@router.get("/occupancy")
async def occupancy(_: Principal = Depends(get_principal)):
    return {"occupancy": 0, "zones": {}}

@router.get("/queue-metrics")
async def queue_metrics(_: Principal = Depends(get_principal)):
    return {"queues": {}, "total_waiting": 0}
