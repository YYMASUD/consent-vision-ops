"""Governance API routes."""
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.deps import get_principal, roles_required
from app.auth.security import Principal
from app.common.enums import REVIEWER_ROLES, AUDIT_ROLES, ROLE_SYSTEM_ADMIN
from app.db.session import get_db
from app.repositories import AlertRuleRepository, AlertRepository, ReviewRepository, AuditRepository
from app.schemas.common import Page
from app.schemas.governance import AlertRuleCreate,AlertRuleRead,AlertRead,ReviewCaseRead,ReviewActionRequest,ReviewActionRead,AuditLogRead
router=APIRouter(tags=['governance'])
def cv(x,t): return t.model_validate(x)
@router.post('/alert-rules',response_model=AlertRuleRead,status_code=201,dependencies=[Depends(roles_required(ROLE_SYSTEM_ADMIN))])
async def create_rule(body:AlertRuleCreate,db:AsyncSession=Depends(get_db),_:Principal=Depends(get_principal)): return cv(await AlertRuleRepository(db).create_rule(**body.model_dump()),AlertRuleRead)
@router.get('/alert-rules',response_model=Page[AlertRuleRead])
async def rules(limit:int=50,cursor:str|None=None,db:AsyncSession=Depends(get_db),_:Principal=Depends(get_principal)):
 a,c=await AlertRuleRepository(db).list_rules(limit=min(limit,100),cursor=cursor); return Page(items=[cv(x,AlertRuleRead) for x in a],next_cursor=c)
@router.get('/alerts',response_model=Page[AlertRead])
async def alerts(limit:int=50,cursor:str|None=None,status:str|None=None,severity:str|None=None,camera_id:uuid.UUID|None=None,db:AsyncSession=Depends(get_db),_:Principal=Depends(get_principal)):
 a,c=await AlertRepository(db).list_alerts(limit=min(limit,100),cursor=cursor,status=status,severity=severity,camera_id=camera_id); return Page(items=[cv(x,AlertRead) for x in a],next_cursor=c)
@router.get('/review-cases',response_model=Page[ReviewCaseRead])
async def cases(limit:int=50,cursor:str|None=None,status:str|None=None,assigned_to:str|None=None,db:AsyncSession=Depends(get_db),_:Principal=Depends(get_principal)):
 a,c=await ReviewRepository(db).list_cases(limit=min(limit,100),cursor=cursor,status=status,assigned_to=assigned_to); return Page(items=[cv(x,ReviewCaseRead) for x in a],next_cursor=c)
@router.post('/review-cases/{id}/actions',response_model=ReviewActionRead,status_code=201,dependencies=[Depends(roles_required(*REVIEWER_ROLES))])
async def add_action(id:uuid.UUID,body:ReviewActionRequest,db:AsyncSession=Depends(get_db),_:Principal=Depends(get_principal)):
 if not await ReviewRepository(db).get(id): raise HTTPException(404,'Review case not found')
 return cv(await ReviewRepository(db).add_action(id,**body.model_dump()),ReviewActionRead)
@router.get('/review-cases/{id}/actions',response_model=list[ReviewActionRead])
async def actions(id:uuid.UUID,db:AsyncSession=Depends(get_db),_:Principal=Depends(get_principal)): return [cv(x,ReviewActionRead) for x in await ReviewRepository(db).actions_for_case(id)]
@router.get('/audit',response_model=Page[AuditLogRead],dependencies=[Depends(roles_required(*AUDIT_ROLES))])
async def audit(limit:int=100,cursor:str|None=None,action:str|None=None,resource_type:str|None=None,actor_id:str|None=None,db:AsyncSession=Depends(get_db),_:Principal=Depends(get_principal)):
 a,c=await AuditRepository(db).list_logs(limit=min(limit,200),cursor=cursor,action=action,resource_type=resource_type,actor_id=actor_id); return Page(items=[cv(x,AuditLogRead) for x in a],next_cursor=c)
