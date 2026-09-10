"""What-If Risk Simulator API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database.connection import get_db
from app.models.database_models import CloudEvent, CloudUserEnforcement, RiskScore, User
from app.models.schemas import SimulateRiskRequest, SimulateRiskResponse
from app.ml.risk.scorer import compute_risk_score
from app.services.feature_engineering import extract_raw_features, extract_derived_features
from app.services.preprocessing import load_processed_dataframe

router = APIRouter()


@router.post("/simulate", response_model=SimulateRiskResponse, summary="Simulate behavior changes on risk score")
async def simulate_risk(
    req: SimulateRiskRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """
    Simulate what happens to a user's risk score when hypothetical behaviors occur.
    Uses the project's native risk scoring function.
    """
    uid = req.cloud_user_id

    # 1. Fetch user events
    stmt = select(CloudEvent).where(CloudEvent.cloud_user_id == uid)
    res = await db.execute(stmt)
    events = res.scalars().all()

    # Base values
    if events:
        df = load_processed_dataframe(events)
        raw = extract_raw_features(df, uid)
        derived = extract_derived_features(df, uid)
        event_count = raw.get("event_count", 10)
        unique_services = raw.get("services", ["s3", "ec2"])
        failed_count = raw.get("failure_count", 0) or 0
    else:
        event_count = 20
        unique_services = ["s3", "ec2"]
        failed_count = 0

    # Base Risk Score
    current_score, current_level, base_factors = compute_risk_score(
        anomaly_score=0.15,
        is_anomaly=False,
        event_count=event_count,
        failed_request_count=failed_count,
        unique_services=unique_services,
        unusual_services=[],
        sensitive_resources=[],
        historical_avg_requests=float(event_count),
        recent_intensity=0.1,
        is_coordinated=False,
        temporal_anomaly_score=None,
    )

    # Simulated parameter adjustments
    sim_anomaly_score = 0.15
    sim_is_anomaly = False
    sim_event_count = event_count
    sim_failed_count = failed_count
    sim_unusual_services = []
    sim_sensitive_resources = []
    sim_recent_intensity = 0.1
    sim_coordinated = req.coordinated_behavior
    sim_temporal_anomaly = 0.8 if req.temporal_anomaly else None

    # Apply toggles
    if req.abnormal_api_activity:
        sim_event_count = max(event_count * 4, 80)
        sim_recent_intensity = 0.95
        sim_anomaly_score = max(sim_anomaly_score, 0.65)

    if req.privilege_escalation:
        sim_anomaly_score = max(sim_anomaly_score, 0.90)
        sim_is_anomaly = True
        sim_sensitive_resources.extend(["arn:aws:iam:::role/AdminAccess", "arn:aws:iam:::policy/RootPrivileges"])
        sim_unusual_services.append("iam")

    if req.sensitive_resource_access:
        sim_sensitive_resources.extend(["arn:aws:secretsmanager:::secret/production_db_creds", "arn:aws:kms:::key/master-enc-key"])
        sim_unusual_services.append("secretsmanager")

    if req.multiple_failed_logins:
        sim_failed_count = max(failed_count + 12, 12)
        sim_event_count = max(sim_event_count, sim_failed_count + 5)

    if req.unusual_login or req.new_ip_location:
        sim_anomaly_score = max(sim_anomaly_score, 0.55)
        sim_unusual_services.append("sts")

    # Compute Simulated Risk Score
    sim_score, sim_level, sim_factors = compute_risk_score(
        anomaly_score=sim_anomaly_score,
        is_anomaly=sim_is_anomaly,
        event_count=sim_event_count,
        failed_request_count=sim_failed_count,
        unique_services=list(set(unique_services + sim_unusual_services)),
        unusual_services=sim_unusual_services,
        sensitive_resources=sim_sensitive_resources,
        historical_avg_requests=float(event_count),
        recent_intensity=sim_recent_intensity,
        is_coordinated=sim_coordinated,
        temporal_anomaly_score=sim_temporal_anomaly,
    )

    delta = round(sim_score - current_score, 1)

    # Determine top contributor
    top_factor = max(sim_factors, key=lambda f: f.contribution) if sim_factors else None
    top_contributor_name = top_factor.factor if top_factor else "Normal Baseline"

    explanation = (
        f"Simulating selected behaviors for '{uid}' increases risk by +{delta:.1f} pts "
        f"(from {current_score:.1f} [{current_level}] to {sim_score:.1f} [{sim_level}]). "
        f"Primary risk driver: {top_contributor_name} ({top_factor.description if top_factor else 'None'})."
    )

    return SimulateRiskResponse(
        cloud_user_id=uid,
        current_risk_score=current_score,
        current_risk_level=current_level,
        simulated_risk_score=sim_score,
        simulated_risk_level=sim_level,
        delta=delta,
        risk_level_changed=current_level != sim_level,
        top_contributor=top_contributor_name,
        explanation=explanation,
        factor_contributions=[f.to_dict() for f in sim_factors],
    )
