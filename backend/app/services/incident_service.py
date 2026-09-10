"""
Incident management service — CloudIntelliGuard.

Creates incidents from anomaly results, manages status transitions,
and auto-generates alerts and recommendations.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger, log_audit
from app.models.database_models import (
    Alert, Anomaly, CoordinatedEvent, GraphWindow, Incident, Recommendation, RiskScore,
)

# Rule-based recommendations by severity
RECOMMENDATIONS_BY_SEVERITY: Dict[str, List[Dict[str, Any]]] = {
    "CRITICAL": [
        {
            "action": "Require immediate re-authentication for this user",
            "rationale": "CRITICAL risk score warrants session invalidation to prevent ongoing access.",
            "priority": 1,
        },
        {
            "action": "Review all sensitive resource accesses in this window",
            "rationale": "Sensitive resources may have been compromised.",
            "priority": 2,
        },
        {
            "action": "Restrict sensitive API operations for this user temporarily",
            "rationale": "Limit blast radius while investigation is ongoing.",
            "priority": 3,
        },
        {
            "action": "Increase monitoring frequency for this user to 1-minute intervals",
            "rationale": "Enhanced monitoring captures ongoing malicious activity.",
            "priority": 4,
        },
    ],
    "HIGH": [
        {
            "action": "Initiate investigation of recent API call sequence",
            "rationale": "HIGH risk score indicates significant behavioral anomaly requiring review.",
            "priority": 1,
        },
        {
            "action": "Increase monitoring for this user",
            "rationale": "Elevated surveillance helps detect escalating behavior.",
            "priority": 2,
        },
        {
            "action": "Review recent access to sensitive services",
            "rationale": "Unusual service access pattern may indicate credential misuse.",
            "priority": 3,
        },
    ],
    "MEDIUM": [
        {
            "action": "Continue observation and verify activity with user if possible",
            "rationale": "MEDIUM risk may indicate legitimate unusual activity; verification recommended.",
            "priority": 1,
        },
        {
            "action": "Log this event for future pattern analysis",
            "rationale": "Aggregating medium-risk events enables pattern detection over time.",
            "priority": 2,
        },
    ],
    "LOW": [
        {
            "action": "Continue standard monitoring",
            "rationale": "LOW risk score is within normal operating range. No immediate action required.",
            "priority": 1,
        },
    ],
}


async def create_incident_from_anomaly(
    db: AsyncSession,
    anomaly: Anomaly,
    risk_score: RiskScore,
    graph_window: GraphWindow,
    created_by_user_id: Optional[int] = None,
) -> Incident:
    """
    Create a security incident from a detected anomaly and its risk score.

    Auto-generates:
      - Alert record
      - Recommendation records (rule-based)

    Returns:
        The created Incident ORM object.
    """
    severity = risk_score.risk_level
    explanation_text = (
        anomaly.explanation.get("summary", "Anomaly detected.")
        if anomaly.explanation else "Anomaly detected."
    )

    # Extract affected services/resources from anomaly explanation
    findings = anomaly.explanation.get("findings", []) if anomaly.explanation else []
    affected_services = _extract_from_findings(findings, "service_access")
    affected_resources = _extract_from_findings(findings, "resource_access")

    incident = Incident(
        title=f"Anomaly detected for user {anomaly.cloud_user_id} [{severity}]",
        severity=severity,
        status="NEW",
        cloud_user_ids=[anomaly.cloud_user_id],
        risk_score=risk_score.risk_score,
        anomaly_score=anomaly.anomaly_score,
        explanation=explanation_text,
        affected_services=affected_services or None,
        affected_resources=affected_resources or None,
        graph_window_id=graph_window.id,
        anomaly_id=anomaly.id,
        is_coordinated=False,
    )
    db.add(incident)
    await db.flush()

    # Create alert
    alert = Alert(
        incident_id=incident.id,
        cloud_user_id=anomaly.cloud_user_id,
        alert_type="ANOMALY",
        message=f"{severity} risk detected for user {anomaly.cloud_user_id}: {explanation_text}",
        severity=severity,
    )
    db.add(alert)

    # Create recommendations
    for rec_data in RECOMMENDATIONS_BY_SEVERITY.get(severity, RECOMMENDATIONS_BY_SEVERITY["LOW"]):
        rec = Recommendation(
            incident_id=incident.id,
            severity=severity,
            action=rec_data["action"],
            rationale=rec_data["rationale"],
            priority=rec_data["priority"],
            is_simulation_only=True,  # NEVER performs real cloud actions
        )
        db.add(rec)

    await db.commit()
    await db.refresh(incident)

    log_audit(
        action="incident_created",
        user_id=created_by_user_id,
        resource=f"incident/{incident.id}",
        detail={
            "cloud_user_id": anomaly.cloud_user_id,
            "severity": severity,
            "risk_score": risk_score.risk_score,
        },
    )

    logger.info(f"Created incident {incident.id}: {severity} for {anomaly.cloud_user_id}")
    return incident


async def create_coordinated_incident(
    db: AsyncSession,
    coord_event: CoordinatedEvent,
    severity: str = "HIGH",
) -> Incident:
    """Create a coordinated security incident from a CoordinatedEvent."""
    user_ids = coord_event.related_cloud_user_ids or []
    incident = Incident(
        title=f"Coordinated suspicious activity detected across {len(user_ids)} user(s)",
        severity=severity,
        status="NEW",
        cloud_user_ids=user_ids,
        explanation=(
            f"Coordinated behavior detected. "
            f"Coordination score: {coord_event.coordination_score:.3f}. "
            f"Users: {', '.join(user_ids[:5])}"
        ),
        affected_services=coord_event.related_services,
        affected_resources=coord_event.related_resources,
        is_coordinated=True,
        coordinated_event_id=coord_event.id,
    )
    db.add(incident)
    await db.flush()

    for uid in user_ids:
        alert = Alert(
            incident_id=incident.id,
            cloud_user_id=uid,
            alert_type="COORDINATED",
            message=(
                f"Coordinated suspicious activity involving user {uid}. "
                f"Score: {coord_event.coordination_score:.3f}"
            ),
            severity=severity,
        )
        db.add(alert)

    for rec_data in RECOMMENDATIONS_BY_SEVERITY.get(severity, []):
        db.add(Recommendation(
            incident_id=incident.id,
            severity=severity,
            action=rec_data["action"],
            rationale=rec_data["rationale"],
            priority=rec_data["priority"],
            is_simulation_only=True,
        ))

    await db.commit()
    await db.refresh(incident)
    logger.info(f"Created coordinated incident {incident.id} for {len(user_ids)} users.")
    return incident


async def update_incident_status(
    db: AsyncSession,
    incident_id: int,
    new_status: str,
    updated_by_user_id: Optional[int] = None,
    note: Optional[str] = None,
) -> Incident:
    """Update incident status with audit logging."""
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if incident is None:
        raise ValueError(f"Incident {incident_id} not found.")

    old_status = incident.status
    incident.status = new_status
    incident.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(incident)

    log_audit(
        action="incident_status_changed",
        user_id=updated_by_user_id,
        resource=f"incident/{incident_id}",
        detail={"old_status": old_status, "new_status": new_status, "note": note},
    )
    return incident


def _extract_from_findings(findings: List[Dict], category: str) -> List[str]:
    """Extract evidence values from explanation findings of a given category."""
    values: List[str] = []
    for f in findings:
        if f.get("category") == category and isinstance(f.get("evidence"), list):
            values.extend(f["evidence"])
    return list(set(values))
