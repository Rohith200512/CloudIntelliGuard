"""Incidents API."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.logging import log_audit
from app.database.connection import get_db
from app.models.database_models import Anomaly, GraphWindow, Incident, RiskScore, User
from app.models.schemas import IncidentCreate, IncidentRead, IncidentStatusUpdate, MessageResponse
from app.services.incident_service import (
    create_incident_from_anomaly, update_incident_status,
)

router = APIRouter()


@router.get("", response_model=List[IncidentRead], summary="List incidents")
async def list_incidents(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
    severity: Optional[str] = Query(None),
    incident_status: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    q = (
        select(Incident)
        .options(
            selectinload(Incident.recommendations),
            selectinload(Incident.alerts),
        )
        .order_by(Incident.created_at.desc())
    )
    if severity:
        q = q.where(Incident.severity == severity.upper())
    if incident_status:
        q = q.where(Incident.status == incident_status.upper())
    q = q.offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{incident_id}", response_model=IncidentRead, summary="Get incident by ID")
async def get_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Incident)
        .options(
            selectinload(Incident.recommendations),
            selectinload(Incident.alerts),
        )
        .where(Incident.id == incident_id)
    )
    incident = result.scalar_one_or_none()
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found.")
    return incident


@router.post("", response_model=IncidentRead, status_code=status.HTTP_201_CREATED,
             summary="Create incident from an anomaly")
async def create_incident(
    body: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a security incident manually from an anomaly record."""
    if body.anomaly_id is None:
        raise HTTPException(status_code=422, detail="anomaly_id is required.")

    a_result = await db.execute(select(Anomaly).where(Anomaly.id == body.anomaly_id))
    anomaly = a_result.scalar_one_or_none()
    if anomaly is None:
        raise HTTPException(status_code=404, detail="Anomaly not found.")

    gw_result = await db.execute(select(GraphWindow).where(GraphWindow.id == anomaly.graph_window_id))
    gw = gw_result.scalar_one_or_none()
    if gw is None:
        raise HTTPException(status_code=404, detail="GraphWindow not found.")

    # Get or compute risk score
    rs_result = await db.execute(
        select(RiskScore)
        .where(RiskScore.anomaly_id == body.anomaly_id)
        .order_by(RiskScore.created_at.desc())
        .limit(1)
    )
    rs = rs_result.scalar_one_or_none()
    if rs is None:
        from app.services.risk_service import compute_and_store_risk
        rs = await compute_and_store_risk(db, anomaly, gw)

    incident = await create_incident_from_anomaly(
        db, anomaly, rs, gw, created_by_user_id=current_user.id
    )
    return incident


@router.patch("/{incident_id}/status", response_model=IncidentRead,
              summary="Update incident status")
async def patch_incident_status(
    incident_id: int,
    body: IncidentStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    incident = await update_incident_status(
        db, incident_id, body.status, current_user.id, body.note
    )
    return incident
