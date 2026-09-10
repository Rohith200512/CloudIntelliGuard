"""Alerts API."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database.connection import get_db
from app.models.database_models import Alert, User
from app.models.schemas import AlertRead
from app.services.alert_service import acknowledge_alert, get_active_alerts

router = APIRouter()


@router.get("", response_model=List[AlertRead], summary="List all alerts")
async def list_alerts(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
    active_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
):
    if active_only:
        return await get_active_alerts(db, limit)
    result = await db.execute(
        select(Alert).order_by(Alert.created_at.desc()).limit(limit)
    )
    return result.scalars().all()


@router.patch("/{alert_id}/acknowledge", response_model=AlertRead,
              summary="Acknowledge an alert")
async def ack_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await acknowledge_alert(db, alert_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
