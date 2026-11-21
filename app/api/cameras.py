"""Camera CRUD, health, and frame-ingestion endpoints (spec §3, §19)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_principal, roles_required
from app.auth.encryption import encrypt_str
from app.auth.security import Principal
from app.common.enums import (
    ROLE_CAMERA_OPERATOR,
    ROLE_SYSTEM_ADMIN,
)
from app.common.utils import AppError, get_request_id, new_id, utcnow
from app.config.settings import get_settings
from app.db.session import get_db
from app.services.ingestion.service import get_ingestion_service

from app.repositories import AuditRepository, CameraRepository, HealthRepository
from app.repositories.base import as_uuid
from app.schemas.common import Page
from app.schemas.ops import CameraCreate, CameraHealthRead, CameraRead, CameraUpdate

router = APIRouter(prefix="/cameras", tags=["cameras"])

_ADMIN_OR_OPERATOR = [ROLE_SYSTEM_ADMIN, ROLE_CAMERA_OPERATOR]


def _orm_to_read(camera) -> CameraRead:
    return CameraRead.model_validate(camera)


async def _audit(
    db: AsyncSession,
    action: str,
    resource_id: str,
    actor_id: str,
) -> None:
    repo = AuditRepository(db)
    await repo.record(
        action,
        "camera",
        actor_id=actor_id,
        resource_id=resource_id,
        request_id=get_request_id(),
    )


@router.post(
    "",
    response_model=CameraRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(roles_required(*_ADMIN_OR_OPERATOR))],
)
async def create_camera(
    body: CameraCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_principal),
):
    settings = get_settings()
    encrypted_url: str | None = None
    if body.stream_url:
        encrypted_url = (
            encrypt_str(body.stream_url) if settings.encryption_key else body.stream_url
        )

    repo = CameraRepository(db)
    camera = await repo.create_camera(
        name=body.name,
        stream_url_encrypted=encrypted_url,
        location_label=body.location_label,
        enabled=body.enabled,
    )
    await _audit(db, "camera.create", str(camera.camera_id), principal.subject_id)
    return _orm_to_read(camera)


@router.get("", response_model=Page[CameraRead])
async def list_cameras(
    limit: int = 50,
    cursor: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: Principal = Depends(get_principal),
):
    repo = CameraRepository(db)
    items, next_cursor = await repo.list_cameras(limit=limit, cursor=cursor)
    return Page(items=[_orm_to_read(c) for c in items], next_cursor=next_cursor)


@router.get("/{camera_id}", response_model=CameraRead)
async def get_camera(
    camera_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Principal = Depends(get_principal),
):
    repo = CameraRepository(db)
    camera = await repo.get(camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    return _orm_to_read(camera)


@router.patch(
    "/{camera_id}",
    response_model=CameraRead,
    dependencies=[Depends(roles_required(*_ADMIN_OR_OPERATOR))],
)
async def update_camera(
    camera_id: uuid.UUID,
    body: CameraUpdate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_principal),
):
    repo = CameraRepository(db)
    camera = await repo.get(camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")

    settings = get_settings()
    if body.name is not None:
        camera.name = body.name
    if body.stream_url is not None:
        camera.stream_url_encrypted = (
            encrypt_str(body.stream_url) if settings.encryption_key else body.stream_url
        )
    if body.location_label is not None:
        camera.location_label = body.location_label
    if body.enabled is not None:
        camera.enabled = body.enabled
    camera.updated_at = utcnow()
    await repo.flush()
    await _audit(db, "camera.update", str(camera_id), principal.subject_id)
    return _orm_to_read(camera)


@router.delete(
    "/{camera_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(roles_required(ROLE_SYSTEM_ADMIN))],
)
async def delete_camera(
    camera_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_principal),
):
    repo = CameraRepository(db)
    deleted = await repo.delete(camera_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Camera not found")
    await _audit(db, "camera.delete", str(camera_id), principal.subject_id)


@router.get("/{camera_id}/health", response_model=list[CameraHealthRead])
async def camera_health(
    camera_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Principal = Depends(get_principal),
):
    """Return the last 20 health events for a camera."""
    # verify camera exists
    cam_repo = CameraRepository(db)
    camera = await cam_repo.get(camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")

    health_repo = HealthRepository(db)
    events = await health_repo.open_incidents(camera_id=camera_id)
    return [CameraHealthRead.model_validate(e) for e in events[:20]]


@router.post("/{camera_id}/frame", status_code=status.HTTP_200_OK)
async def ingest_frame(
    camera_id: uuid.UUID,
    file: UploadFile = File(..., description="JPEG or PNG frame"),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_principal),
):
    """Upload a JPEG/PNG frame; run ingestion the ingestion pipeline."""
    cam_repo = CameraRepository(db)
    camera = await cam_repo.get(camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")

    content_type = file.content_type or ""
    if content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(
            status_code=422, detail="Only JPEG and PNG frames are accepted"
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="Empty frame body")

    service = get_ingestion_service()
    result = await service.process_frame(str(camera_id), raw, frame_number=0)
    return {
        "camera_id": str(camera_id),
        "frame_number": result.frame_number,
        "frame_bytes": len(raw),
        "detections": [d.to_dict() if hasattr(d, "to_dict") else d for d in result.person_detections],
        "tracks": [t.to_dict() if hasattr(t, "to_dict") else t for t in result.tracks],
        "occupancy": result.occupancy,
        "zone_events": result.zone_events,
        "processed_at": result.timestamp.isoformat(),
    }
