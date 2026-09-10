"""Risk scores API."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database.connection import get_db
from app.models.database_models import Anomaly, GraphWindow, RiskScore, User
from app.models.schemas import RiskScoreRead
from app.services.risk_service import compute_and_store_risk, get_user_risk_history

router = APIRouter()


@router.get("", response_model=List[RiskScoreRead], summary="List risk scores")
async def list_risk_scores(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
    cloud_user_id: Optional[str] = Query(None),
    graph_window_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    q = select(RiskScore).order_by(RiskScore.created_at.desc())
    if cloud_user_id:
        q = q.where(RiskScore.cloud_user_id == cloud_user_id)
    if graph_window_id:
        q = q.where(RiskScore.graph_window_id == graph_window_id)
    q = q.offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/compute/{anomaly_id}", response_model=RiskScoreRead,
             summary="Compute and store risk score for an anomaly")
async def compute_risk(
    anomaly_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Compute and persist a risk score from an existing anomaly record."""
    a_result = await db.execute(select(Anomaly).where(Anomaly.id == anomaly_id))
    anomaly = a_result.scalar_one_or_none()
    if anomaly is None:
        raise HTTPException(status_code=404, detail="Anomaly not found.")

    gw_result = await db.execute(select(GraphWindow).where(GraphWindow.id == anomaly.graph_window_id))
    gw = gw_result.scalar_one_or_none()
    if gw is None:
        raise HTTPException(status_code=404, detail="GraphWindow not found.")

    rs = await compute_and_store_risk(db, anomaly, gw)
    return rs


@router.get("/user/{cloud_user_id}/history", response_model=List[RiskScoreRead],
            summary="Get risk score history for a cloud user")
async def user_risk_history(
    cloud_user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
):
    return await get_user_risk_history(db, cloud_user_id, limit)
