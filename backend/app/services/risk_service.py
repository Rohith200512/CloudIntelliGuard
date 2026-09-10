"""
Risk scoring service — CloudIntelliGuard.

Orchestrates context computation and persists RiskScore records to the database.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.database_models import Anomaly, CloudEvent, GraphWindow, RiskScore
from app.ml.risk.scorer import compute_risk_score, RiskFactorResult
from app.services.feature_engineering import (
    extract_raw_features, extract_derived_features,
    SENSITIVE_SERVICES,
)
from app.services.preprocessing import load_processed_dataframe

# Services we consider "unusual" if not seen before in historical data
_COMMON_SERVICES = {"s3", "ec2", "cloudwatch", "elb", "lambda"}


async def compute_and_store_risk(
    db: AsyncSession,
    anomaly: Anomaly,
    graph_window: GraphWindow,
    is_coordinated: bool = False,
) -> RiskScore:
    """
    Compute context-aware risk score for a user and persist it.

    Args:
        db: Async database session
        anomaly: The Anomaly record for this user/window
        graph_window: The GraphWindow containing the events
        is_coordinated: Whether user is part of a coordinated event

    Returns:
        Persisted RiskScore ORM object.
    """
    # Load events for this window
    events_result = await db.execute(
        select(CloudEvent).where(
            CloudEvent.dataset_id == graph_window.dataset_id,
            CloudEvent.timestamp >= graph_window.start_time,
            CloudEvent.timestamp < graph_window.end_time,
        )
    )
    events = events_result.scalars().all()
    df = load_processed_dataframe(events)

    uid = anomaly.cloud_user_id
    raw = extract_raw_features(df, uid)
    derived = extract_derived_features(
        df, uid,
        window_start=graph_window.start_time,
        window_end=graph_window.end_time,
    )

    unique_services: List[str] = raw.get("services", [])
    user_services_lower = set(s.lower() for s in unique_services)
    unusual_services = [
        s for s in unique_services
        if s.lower() not in _COMMON_SERVICES
    ]
    sensitive_resources: List[str] = derived.get("sensitive_resources", [])

    risk_score, risk_level, factors = compute_risk_score(
        anomaly_score=anomaly.anomaly_score,
        is_anomaly=anomaly.is_anomaly,
        event_count=raw.get("event_count", 0),
        failed_request_count=derived.get("failed_count", 0) or 0,
        unique_services=unique_services,
        unusual_services=unusual_services,
        sensitive_resources=sensitive_resources,
        historical_avg_requests=derived.get("historical_avg_daily_requests"),
        recent_intensity=derived.get("recent_intensity"),
        is_coordinated=is_coordinated,
        temporal_anomaly_score=None,
    )

    rs = RiskScore(
        cloud_user_id=uid,
        graph_window_id=graph_window.id,
        anomaly_id=anomaly.id,
        risk_score=risk_score,
        risk_level=risk_level,
        factors=[f.to_dict() for f in factors],
    )
    db.add(rs)
    await db.commit()
    await db.refresh(rs)

    # Autonomous Security Response Policy Trigger
    from app.services.response_service import evaluate_and_enforce_user_risk
    reason_desc = f"{risk_level} risk score ({risk_score:.1f}) in Window #{graph_window.id}"
    await evaluate_and_enforce_user_risk(
        db=db,
        cloud_user_id=uid,
        risk_score=risk_score,
        risk_level=risk_level,
        reason=reason_desc,
        trigger_anomaly_id=anomaly.id,
    )

    logger.info(f"Risk scored for {uid}: {risk_score} ({risk_level})")
    return rs


async def get_user_risk_history(
    db: AsyncSession,
    cloud_user_id: str,
    limit: int = 20,
) -> List[RiskScore]:
    """Return recent risk scores for a cloud user (newest first)."""
    result = await db.execute(
        select(RiskScore)
        .where(RiskScore.cloud_user_id == cloud_user_id)
        .order_by(RiskScore.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()
