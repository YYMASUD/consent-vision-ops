from app.common.utils import utcnow

from datetime import datetime

from app.schemas.governance import RetentionRunResult

from app.common.enums import ALERT_ACKNOWLEDGED, ALERT_RESOLVED, CASE_CLOSED, CASE_IN_REVIEW
from app.schemas.governance import AlertAssignRequest, AlertAckRequest, AlertResolveRequest

"""Governance API routes."""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.deps import get_principal, roles_required
from app.auth.security import Principal
from app.common.enums import AUDIT_ROLES, REVIEWER_ROLES, ROLE_PRIVACY_OFFICER, ROLE_SYSTEM_ADMIN
from app.db.session import get_db
from app.repositories import AlertRepository, AlertRuleRepository, AuditRepository, ReviewRepository
from app.schemas.common import Page
from app.schemas.governance import AlertRead, AlertRuleCreate, AlertRuleRead, AuditLogRead, ReviewActionRead, ReviewActionRequest, ReviewCaseRead
from app.services.retention.service import RetentionService

router = APIRouter(tags=["governance"])

def _read(value, schema):
    return schema.model_validate(value)

@router.post("/alert-rules", response_model=AlertRuleRead, status_code=201, dependencies=[Depends(roles_required(ROLE_SYSTEM_ADMIN))])
async def create_rule(body: AlertRuleCreate, db: AsyncSession = Depends(get_db), _: Principal = Depends(get_principal)):
    return _read(await AlertRuleRepository(db).create_rule(**body.model_dump()), AlertRuleRead)

@router.get("/alert-rules", response_model=Page[AlertRuleRead])
async def list_rules(limit: int = 50, cursor: str | None = None, db: AsyncSession = Depends(get_db), _: Principal = Depends(get_principal)):
    rows, next_cursor = await AlertRuleRepository(db).list_rules(limit=min(max(limit, 1), 100), cursor=cursor)
    return Page(items=[_read(row, AlertRuleRead) for row in rows], next_cursor=next_cursor)

@router.get("/alerts", response_model=Page[AlertRead])
async def list_alerts(limit: int = 50, cursor: str | None = None, status: str | None = None, severity: str | None = None, camera_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_db), _: Principal = Depends(get_principal)):
    rows, next_cursor = await AlertRepository(db).list_alerts(limit=min(max(limit, 1), 100), cursor=cursor, status=status, severity=severity, camera_id=camera_id)
    return Page(items=[_read(row, AlertRead) for row in rows], next_cursor=next_cursor)

@router.get("/review-cases", response_model=Page[ReviewCaseRead])
async def list_cases(limit: int = 50, cursor: str | None = None, status: str | None = None, assigned_to: str | None = None, db: AsyncSession = Depends(get_db), _: Principal = Depends(get_principal)):
    rows, next_cursor = await ReviewRepository(db).list_cases(limit=min(max(limit, 1), 100), cursor=cursor, status=status, assigned_to=assigned_to)
    return Page(items=[_read(row, ReviewCaseRead) for row in rows], next_cursor=next_cursor)


@router.patch("/alerts/{alert_id}/assign", response_model=AlertRead, dependencies=[Depends(roles_required(*REVIEWER_ROLES))])
async def assign_alert(alert_id: uuid.UUID, body: AlertAssignRequest, db: AsyncSession = Depends(get_db), _: Principal = Depends(get_principal)):
    obj = await AlertRepository(db).get(alert_id)
    if obj is None: raise HTTPException(404, "Alert not found")
    obj.assigned_to = body.assigned_to
    await db.flush()
    return _read(obj, AlertRead)

@router.post("/alerts/{alert_id}/ack", response_model=AlertRead, dependencies=[Depends(roles_required(*REVIEWER_ROLES))])
async def acknowledge_alert(alert_id: uuid.UUID, body: AlertAckRequest, db: AsyncSession = Depends(get_db), _: Principal = Depends(get_principal)):
    obj = await AlertRepository(db).get(alert_id)
    if obj is None: raise HTTPException(404, "Alert not found")
    obj.status = ALERT_ACKNOWLEDGED
    from app.common.utils import utcnow
    obj.acknowledged_at = utcnow(); await db.flush(); return _read(obj, AlertRead)

@router.post("/alerts/{alert_id}/resolve", response_model=AlertRead, dependencies=[Depends(roles_required(*REVIEWER_ROLES))])
async def resolve_alert(alert_id: uuid.UUID, body: AlertResolveRequest, db: AsyncSession = Depends(get_db), _: Principal = Depends(get_principal)):
    obj = await AlertRepository(db).get(alert_id)
    if obj is None: raise HTTPException(404, "Alert not found")
    obj.status = ALERT_RESOLVED
    from app.common.utils import utcnow
    obj.resolved_at = utcnow()
    if body.notes: obj.details = {**(obj.details or {}), "resolution_notes": body.notes}
    await db.flush(); return _read(obj, AlertRead)

    rows, next_cursor = await ReviewRepository(db).list_cases(limit=min(max(limit, 1), 100), cursor=cursor, status=status, assigned_to=assigned_to)
    return Page(items=[_read(row, ReviewCaseRead) for row in rows], next_cursor=next_cursor)

@router.post("/review-cases/{case_id}/actions", response_model=ReviewActionRead, status_code=201, dependencies=[Depends(roles_required(*REVIEWER_ROLES))])
async def add_action(case_id: uuid.UUID, body: ReviewActionRequest, db: AsyncSession = Depends(get_db), _: Principal = Depends(get_principal)):
    repo = ReviewRepository(db)
    if await repo.get(case_id) is None:
        raise HTTPException(status_code=404, detail="Review case not found")
    return _read(await repo.add_action(case_id, **body.model_dump()), ReviewActionRead)

@router.get("/review-cases/{case_id}/actions", response_model=list[ReviewActionRead])
async def list_actions(case_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: Principal = Depends(get_principal)):
    return [_read(row, ReviewActionRead) for row in await ReviewRepository(db).actions_for_case(case_id)]

@router.get("/audit", response_model=Page[AuditLogRead], dependencies=[Depends(roles_required(*AUDIT_ROLES))])
async def list_audit(limit: int = 100, cursor: str | None = None, action: str | None = None, resource_type: str | None = None, actor_id: str | None = None, db: AsyncSession = Depends(get_db), _: Principal = Depends(get_principal)):
    rows, next_cursor = await AuditRepository(db).list_logs(limit=min(max(limit, 1), 200), cursor=cursor, action=action, resource_type=resource_type, actor_id=actor_id)
    return Page(items=[_read(row, AuditLogRead) for row in rows], next_cursor=next_cursor)

@router.post("/retention/run", dependencies=[Depends(roles_required(ROLE_SYSTEM_ADMIN, ROLE_PRIVACY_OFFICER))])
async def run_retention(db: AsyncSession = Depends(get_db), principal: Principal = Depends(get_principal)):
    result = await RetentionService.run_sweep(db)
    await AuditRepository(db).record("retention.run", "retention", actor_id=principal.subject_id, metadata=result)
    return result
