"""Consent management endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_principal, roles_required
from app.auth.security import Principal
from app.common.enums import ROLE_ENROLLMENT_MANAGER, ROLE_SYSTEM_ADMIN
from app.common.utils import get_request_id, utcnow
from app.db.session import get_db
from app.repositories import AuditRepository, ConsentRepository
from app.schemas.common import Page
from app.schemas.persons import ConsentCreate, ConsentRead

router = APIRouter(prefix="/consents", tags=["consents"])

_ENROLL_OR_ADMIN = [ROLE_ENROLLMENT_MANAGER, ROLE_SYSTEM_ADMIN]


def _to_read(consent) -> ConsentRead:
    return ConsentRead.model_validate(consent)


async def _audit(db, action, resource_id, actor_id):
    await AuditRepository(db).record(
        action, "consent", actor_id=actor_id, resource_id=resource_id, request_id=get_request_id()
    )


@router.post(
    "",
    response_model=ConsentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(roles_required(*_ENROLL_OR_ADMIN))],
)
async def create_consent(
    body: ConsentCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_principal),
):
    repo = ConsentRepository(db)
    consent = await repo.create_consent(
        person_id=body.person_id,
        purpose=body.purpose,
        allowed_camera_ids=[str(c) for c in body.allowed_camera_ids] if body.allowed_camera_ids else None,
        allowed_zone_ids=[str(z) for z in body.allowed_zone_ids] if body.allowed_zone_ids else None,
        valid_from=body.valid_from,
        valid_until=body.valid_until,
        evidence_reference=body.evidence_reference,
    )
    await _audit(db, "consent.create", str(consent.consent_id), principal.subject_id)
    return _to_read(consent)


@router.get("", response_model=Page[ConsentRead])
async def list_consents(
    person_id: uuid.UUID | None = None,
    limit: int = 50,
    cursor: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: Principal = Depends(get_principal),
):
    repo = ConsentRepository(db)
    if person_id is not None:
        items = await repo.list_by_person(person_id)
        return Page(items=[_to_read(c) for c in items], next_cursor=None)
    items, next_cursor = await repo.list_page(limit=limit, cursor=cursor)
    return Page(items=[_to_read(c) for c in items], next_cursor=next_cursor)


@router.get("/{consent_id}", response_model=ConsentRead)
async def get_consent(
    consent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Principal = Depends(get_principal),
):
    repo = ConsentRepository(db)
    consent = await repo.get(consent_id)
    if consent is None:
        raise HTTPException(status_code=404, detail="Consent not found")
    return _to_read(consent)


@router.delete(
    "/{consent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(roles_required(*_ENROLL_OR_ADMIN))],
)
async def revoke_consent(
    consent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_principal),
):
    repo = ConsentRepository(db)
    n = await repo.revoke(consent_id, when=utcnow())
    if not n:
        raise HTTPException(status_code=404, detail="Consent not found or already revoked")
    await _audit(db, "consent.revoke", str(consent_id), principal.subject_id)
