"""Attack Path Analysis API endpoints."""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database.connection import get_db
from app.models.database_models import User
from app.models.schemas import AttackPath
from app.services.attack_path_service import get_attack_paths

router = APIRouter()


@router.get("", response_model=List[AttackPath], summary="Get detected multi-hop attack paths")
async def list_attack_paths(
    user_id: Optional[str] = Query(None, description="Filter by cloud user ID"),
    resource: Optional[str] = Query(None, description="Filter by target resource"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Retrieve multi-hop attack paths tracing from users/IPs through actions to services/resources."""
    return await get_attack_paths(db, cloud_user_id=user_id, target_resource=resource)
