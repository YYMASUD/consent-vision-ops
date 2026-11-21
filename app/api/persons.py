"""PersonProfile CRUD endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_principal, roles_required
from app.auth.security import Principal
from app.common.enums import ROLE_ENROLLMENT_MANAGER, ROLE_SYSTEM_ADMIN
from app.common.utils import get_request_id, utcnow
from app.db.session import get_db
from app.repositories import AuditRepository, PersonRepository
from app.schemas.common import Page
from app.schemas.persons import PersonCreate, PersonRead, PersonUpdate

router = APIRouter(prefix="/persons", tags=["persons"])

_ENROLL_OR_ADMIN = [ROLE_ENROLLMENT_MANAGER, ROLE_SYSTEM_ADMIN]


def _to_read(person) -> PersonRead:
    return PersonRead.model_validate(person)


async def _audit(db, action, resource_id, actor_id):
    await AuditRepository(db).record(
        action, "person", actor_id=actor_id, resource_id=resource_id, request_id=get_request_id()
    )


@router.post(
    "",
    response_model=PersonRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(roles_required(*_ENROLL_OR_ADMIN))],
)
async def create_person(
    body: PersonCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_principal),
):
    repo = PersonRepository(db)
    person = await repo.create_person(
        display_name=body.display_name,
        access_role=body.access_role,
        external_reference=body.external_reference,
    )
    await _audit(db, "person.create", str(person.person_id), principal.subject_id)
    return _to_read(person)


@router.get("", response_model=Page[PersonRead])
async def list_persons(
    limit: int = 50,
    cursor: str | None = None,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    _: Principal = Depends(get_principal),
):
    repo = PersonRepository(db)
    items, next_cursor = await repo.list_persons(limit=limit, cursor=cursor, active_only=active_only)
    return Page(items=[_to_read(p) for p in items], next_cursor=next_cursor)


@router.get("/{person_id}", response_model=PersonRead)
async def get_person(
    person_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Principal = Depends(get_principal),
):
    repo = PersonRepository(db)
    person = await repo.get(person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return _to_read(person)


@router.patch(
    "/{person_id}",
    response_model=PersonRead,
    dependencies=[Depends(roles_required(*_ENROLL_OR_ADMIN))],
)
async def update_person(
    person_id: uuid.UUID,
    body: PersonUpdate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_principal),
):
    repo = PersonRepository(db)
    person = await repo.get(person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(person, field, value)
    person.updated_at = utcnow()
    await repo.flush()
    return _to_read(person)


@router.delete(
    "/{person_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(roles_required(ROLE_SYSTEM_ADMIN))],
)
async def delete_person(
    person_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_principal),
):
    repo = PersonRepository(db)
    deleted = await repo.delete(person_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Person not found")
    await _audit(db, "person.delete", str(person_id), principal.subject_id)
