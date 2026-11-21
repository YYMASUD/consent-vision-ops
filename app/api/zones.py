"""CameraZone CRUD endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_principal, roles_required
from app.auth.security import Principal
from app.common.enums import ROLE_CAMERA_OPERATOR, ROLE_SYSTEM_ADMIN
from app.common.utils import get_request_id
from app.db.session import get_db
from app.repositories import AuditRepository, ZoneRepository
from app.schemas.common import Page
from app.schemas.ops import ZoneCreate, ZoneRead, ZoneUpdate

router = APIRouter(prefix="/zones", tags=["zones"])

_ADMIN_OR_OPERATOR = [ROLE_SYSTEM_ADMIN, ROLE_CAMERA_OPERATOR]


def _to_read(zone) -> ZoneRead:
    return ZoneRead.model_validate(zone)


async def _audit(db, action, resource_id, actor_id):
    repo = AuditRepository(db)
    await repo.record(action, "zone", actor_id=actor_id, resource_id=resource_id, request_id=get_request_id())


@router.post(
    "",
    response_model=ZoneRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(roles_required(*_ADMIN_OR_OPERATOR))],
)
async def create_zone(
    body: ZoneCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_principal),
):
    repo = ZoneRepository(db)
    zone = await repo.create_zone(
        camera_id=body.camera_id,
        name=body.name,
        polygon=body.polygon,
        zone_type=body.zone_type,
        access_policy=body.access_policy,
        max_occupancy=body.max_occupancy,
        enabled=body.enabled,
    )
    await _audit(db, "zone.create", str(zone.zone_id), principal.subject_id)
    return _to_read(zone)


@router.get("", response_model=Page[ZoneRead])
async def list_zones(
    camera_id: uuid.UUID | None = None,
    limit: int = 50,
    cursor: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: Principal = Depends(get_principal),
):
    repo = ZoneRepository(db)
    items, next_cursor = await repo.list_zones(camera_id=camera_id, limit=limit, cursor=cursor)
    return Page(items=[_to_read(z) for z in items], next_cursor=next_cursor)


@router.get("/{zone_id}", response_model=ZoneRead)
async def get_zone(
    zone_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Principal = Depends(get_principal),
):
    repo = ZoneRepository(db)
    zone = await repo.get(zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    return _to_read(zone)


@router.patch(
    "/{zone_id}",
    response_model=ZoneRead,
    dependencies=[Depends(roles_required(*_ADMIN_OR_OPERATOR))],
)
async def update_zone(
    zone_id: uuid.UUID,
    body: ZoneUpdate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_principal),
):
    repo = ZoneRepository(db)
    zone = await repo.get(zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(zone, field, value)
    await repo.flush()
    await _audit(db, "zone.update", str(zone_id), principal.subject_id)
    return _to_read(zone)


@router.delete(
    "/{zone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(roles_required(ROLE_SYSTEM_ADMIN))],
)
async def delete_zone(
    zone_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_principal),
):
    repo = ZoneRepository(db)
    deleted = await repo.delete(zone_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Zone not found")
    await _audit(db, "zone.delete", str(zone_id), principal.subject_id)
