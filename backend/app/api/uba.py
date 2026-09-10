"""User Behavior Analytics (UBA) API endpoints."""
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database.connection import get_db
from app.models.database_models import User
from app.models.schemas import UBAProfile
from app.services.uba_service import compute_user_uba_profile, get_all_uba_users

router = APIRouter()


@router.get("/users", response_model=List[Dict[str, Any]], summary="List all monitored users for UBA")
async def list_uba_users(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Return all monitored cloud IAM identities with risk summaries for UBA selection."""
    return await get_all_uba_users(db)


@router.get("/profile/{cloud_user_id}", response_model=UBAProfile, summary="Get user behavior profile & deviation")
async def get_user_uba_profile(
    cloud_user_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Get baseline vs current behavior analysis, deviation score, and suspicious indicators."""
    return await compute_user_uba_profile(db, cloud_user_id)
