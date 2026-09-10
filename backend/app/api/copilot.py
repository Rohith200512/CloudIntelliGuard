"""AI Copilot Security Assistant API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database.connection import get_db
from app.models.database_models import User
from app.models.schemas import CopilotQueryRequest, CopilotQueryResponse
from app.services.copilot_service import answer_copilot_query

router = APIRouter()


@router.post("/query", response_model=CopilotQueryResponse, summary="Query AI Security Copilot")
async def query_copilot(
    req: CopilotQueryRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """
    Ask the AI Security Copilot natural language questions regarding threats,
    anomalies, user behavioral profiles, attack paths, and automated actions.
    """
    res = await answer_copilot_query(
        db=db,
        query=req.query,
        context_user_id=req.context_user_id,
        context_incident_id=req.context_incident_id,
    )
    return CopilotQueryResponse(**res)
