"""Cloud events query API."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database.connection import get_db
from app.models.database_models import CloudEvent, User
from app.models.schemas import CloudEventRead

router = APIRouter()


@router.get("", response_model=List[CloudEventRead], summary="List cloud events")
async def list_events(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
    dataset_id: Optional[int] = Query(None),
    cloud_user_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    q = select(CloudEvent).order_by(CloudEvent.timestamp.desc())
    if dataset_id is not None:
        q = q.where(CloudEvent.dataset_id == dataset_id)
    if cloud_user_id is not None:
        q = q.where(CloudEvent.cloud_user_id == cloud_user_id)
    q = q.offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()
