"""Reports API."""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database.connection import get_db
from app.models.database_models import User
from app.services.report_service import generate_security_report

router = APIRouter()


@router.get("/security", summary="Generate a security summary report")
async def security_report(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
    hours: int = Query(24, ge=1, le=720, description="Time window in hours to report on"),
) -> Dict[str, Any]:
    """Generate a security report summarising anomalies, incidents, and risk scores."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours)
    return await generate_security_report(db, start_time=start, end_time=now)
