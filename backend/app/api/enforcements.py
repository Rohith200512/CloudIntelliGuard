"""Automated Response & User Enforcement API endpoints."""
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, require_admin
from app.database.connection import get_db
from app.models.database_models import CloudUserEnforcement, User
from app.models.schemas import (
    AutomatedPolicySummary, EnforcementOverrideRequest, EnforcementRead, MessageResponse,
)
from app.services.response_service import (
    AUTOMATED_POLICIES, get_all_enforcements, manual_override_enforcement,
)

router = APIRouter()


@router.get("", response_model=List[EnforcementRead], summary="List all cloud user enforcements")
async def list_enforcements(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """List all cloud user security status enforcements (Active, Restricted, Blocked)."""
    return await get_all_enforcements(db)


@router.get("/summary", response_model=AutomatedPolicySummary, summary="Get automated response policy summary")
async def get_policy_summary(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Get automated response policies and summary metrics."""
    enfs = await get_all_enforcements(db)
    active = sum(1 for e in enfs if e.status == "ACTIVE")
    restricted = sum(1 for e in enfs if e.status == "RESTRICTED")
    blocked = sum(1 for e in enfs if e.status == "BLOCKED")

    return AutomatedPolicySummary(
        total_monitored_users=len(enfs),
        active_users=active,
        restricted_users=restricted,
        blocked_users=blocked,
        policies=AUTOMATED_POLICIES,
    )


@router.post("/override", response_model=EnforcementRead, summary="Manually override enforcement state")
async def override_enforcement(
    req: EnforcementOverrideRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Manually restore, restrict, or block a cloud identity (Admin only)."""
    try:
        return await manual_override_enforcement(
            db=db,
            cloud_user_id=req.cloud_user_id,
            action=req.action,
            reason=req.reason or "Manual analyst override",
            analyst_user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
