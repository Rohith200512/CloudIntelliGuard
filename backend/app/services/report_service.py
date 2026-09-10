"""Report generation service — aggregates real DB data, no hard-coded stats."""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.database_models import (
    Alert, Anomaly, CloudEvent, Dataset, GraphWindow, Incident, ModelRun, RiskScore,
)


async def generate_dashboard_summary(db: AsyncSession) -> Dict[str, Any]:
    """Aggregate real counts from the database for dashboard summary."""
    total_datasets = await _count(db, Dataset)
    total_events = await _count(db, CloudEvent)
    total_anomalies = await _count(db, Anomaly)
    total_incidents = await _count(db, Incident)

    open_result = await db.execute(
        select(func.count()).select_from(Incident)
        .where(Incident.status.in_(["NEW", "INVESTIGATING"]))
    )
    open_incidents = open_result.scalar() or 0

    crit_result = await db.execute(
        select(func.count()).select_from(Incident)
        .where(Incident.severity == "CRITICAL")
    )
    critical_incidents = crit_result.scalar() or 0

    total_alerts = await _count(db, Alert)
    unack_result = await db.execute(
        select(func.count()).select_from(Alert).where(Alert.acknowledged == False)  # noqa: E712
    )
    unacknowledged_alerts = unack_result.scalar() or 0

    last_run_result = await db.execute(
        select(ModelRun.created_at).order_by(ModelRun.created_at.desc()).limit(1)
    )
    last_run_row = last_run_result.fetchone()
    last_model_run = last_run_row[0] if last_run_row else None

    return {
        "total_datasets": total_datasets,
        "total_events": total_events,
        "total_anomalies": total_anomalies,
        "total_incidents": total_incidents,
        "open_incidents": open_incidents,
        "critical_incidents": critical_incidents,
        "total_alerts": total_alerts,
        "unacknowledged_alerts": unacknowledged_alerts,
        "last_model_run": last_model_run,
        "demo_mode": settings.demo_mode,
    }


async def generate_security_report(
    db: AsyncSession,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Generate a security summary report from real database records."""
    now = datetime.now(timezone.utc)
    report: Dict[str, Any] = {
        "generated_at": now.isoformat(),
        "time_range_start": start_time.isoformat() if start_time else None,
        "time_range_end": end_time.isoformat() if end_time else now.isoformat(),
    }

    # Anomaly breakdown
    anomaly_result = await db.execute(
        select(func.count(), func.avg(Anomaly.anomaly_score))
        .select_from(Anomaly)
    )
    anom_row = anomaly_result.fetchone()
    report["anomaly_count"] = anom_row[0] or 0
    report["avg_anomaly_score"] = round(anom_row[1], 4) if anom_row[1] else None

    # Incident breakdown by severity
    for sev in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
        cnt_result = await db.execute(
            select(func.count()).select_from(Incident).where(Incident.severity == sev)
        )
        report[f"incidents_{sev.lower()}"] = cnt_result.scalar() or 0

    # Risk score distribution
    risk_result = await db.execute(
        select(func.count(), func.avg(RiskScore.risk_score), func.max(RiskScore.risk_score))
        .select_from(RiskScore)
    )
    risk_row = risk_result.fetchone()
    report["risk_score_count"] = risk_row[0] or 0
    report["avg_risk_score"] = round(risk_row[1], 2) if risk_row[1] else None
    report["max_risk_score"] = round(risk_row[2], 2) if risk_row[2] else None

    return report


async def _count(db: AsyncSession, model) -> int:
    result = await db.execute(select(func.count()).select_from(model))
    return result.scalar() or 0
