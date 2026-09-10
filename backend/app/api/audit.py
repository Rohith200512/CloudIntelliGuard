"""Audit Log API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database.connection import get_db
from app.models.database_models import AuditLog, User
from app.models.schemas import AuditLogRead

router = APIRouter()


@router.get("", response_model=List[AuditLogRead], summary="List security audit logs")
async def list_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action type"),
    limit: int = Query(100, ge=1, le=1000, description="Max logs to return"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Retrieve chronological audit trail of automated actions, restrictions, blocks, and manual overrides."""
    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc())
    if action:
        stmt = stmt.where(AuditLog.action.like(f"%{action}%"))
    
    result = await db.execute(stmt.limit(limit))
    return list(result.scalars().all())
