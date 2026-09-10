"""Evaluation and dashboard API."""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database.connection import get_db
from app.models.database_models import EvaluationResult, ModelRun, User
from app.models.schemas import DashboardSummary, EvaluationResultRead
from app.services.report_service import generate_dashboard_summary

router = APIRouter()


@router.get("/results", response_model=List[EvaluationResultRead],
            summary="List model evaluation results")
async def list_eval_results(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
    model_run_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Returns evaluation results.

    NOTE: Results are only present when model evaluation has been run against
    ground-truth labels. If the model has not been evaluated, this returns an
    empty list — not fabricated metrics.
    """
    q = select(EvaluationResult).order_by(EvaluationResult.created_at.desc())
    if model_run_id is not None:
        q = q.where(EvaluationResult.model_run_id == model_run_id)
    q = q.offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/dashboard/summary", response_model=DashboardSummary,
            summary="Dashboard summary (real DB aggregates)")
async def dashboard_summary(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DashboardSummary:
    """Aggregate counts from the database. All values are real, not hardcoded."""
    data = await generate_dashboard_summary(db)
    return DashboardSummary(**data)
