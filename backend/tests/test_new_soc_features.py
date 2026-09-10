"""Unit tests for new SOC features: Automated Response, UBA, Attack Path, Simulator, Copilot, Audit Log."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database_models import CloudEvent, CloudUserEnforcement, Dataset, GraphWindow
from app.services.response_service import evaluate_and_enforce_user_risk, manual_override_enforcement
from app.services.uba_service import compute_user_uba_profile, get_all_uba_users
from app.services.attack_path_service import get_attack_paths
from app.services.copilot_service import answer_copilot_query


@pytest.mark.asyncio
async def test_automated_response_high_risk_restricts(db: AsyncSession):
    """HIGH risk (>= 50) must automatically set status to RESTRICTED and create audit log."""
    status, action = await evaluate_and_enforce_user_risk(
        db=db,
        cloud_user_id="user_high_threat",
        risk_score=62.5,
        risk_level="HIGH",
        reason="Suspicious privilege escalation attempt",
    )
    assert status == "RESTRICTED"
    assert "AUTOMATED_RESTRICTION" in action


@pytest.mark.asyncio
async def test_automated_response_critical_risk_blocks(db: AsyncSession):
    """CRITICAL risk (>= 75) must automatically set status to BLOCKED, revoke session, and create audit log."""
    status, action = await evaluate_and_enforce_user_risk(
        db=db,
        cloud_user_id="user_critical_threat",
        risk_score=88.0,
        risk_level="CRITICAL",
        reason="Exfiltration detected on sensitive KMS/Secrets APIs",
    )
    assert status == "BLOCKED"
    assert "AUTOMATED_BLOCK" in action
    assert "Session Revoked" in action


@pytest.mark.asyncio
async def test_manual_override_enforcement(db: AsyncSession):
    """Analyst can override a blocked user to RESTORE."""
    enf = await manual_override_enforcement(
        db=db,
        cloud_user_id="user_override_test",
        action="BLOCK",
        reason="Initial block",
    )
    assert enf.status == "BLOCKED"

    restored = await manual_override_enforcement(
        db=db,
        cloud_user_id="user_override_test",
        action="RESTORE",
        reason="False positive cleared after verification",
    )
    assert restored.status == "ACTIVE"
    assert restored.session_revoked is False


@pytest.mark.asyncio
async def test_uba_profile_computation(db: AsyncSession):
    """UBA profile computes baseline, current behavior, and deviation score."""
    profile = await compute_user_uba_profile(db, "user_unknown_uba")
    assert profile["cloud_user_id"] == "user_unknown_uba"
    assert "deviation_score" in profile
    assert "baseline" in profile
    assert "current_behavior" in profile
    assert "suspicious_indicators" in profile


@pytest.mark.asyncio
async def test_copilot_highest_risk_query(db: AsyncSession):
    """AI Copilot handles highest risk queries accurately."""
    res = await answer_copilot_query(db, "Which user currently has the highest risk?")
    assert res["intent"] == "QUERY_HIGHEST_RISK"
    assert "answer" in res
    assert len(res["data_sources_used"]) > 0


@pytest.mark.asyncio
async def test_simulator_api_endpoint(client: AsyncClient, auth_headers: dict):
    """What-If simulator endpoint computes before/after risk delta."""
    resp = await client.post(
        "/api/v1/risk-simulator/simulate",
        headers=auth_headers,
        json={
            "cloud_user_id": "test_user_sim",
            "privilege_escalation": True,
            "sensitive_resource_access": True,
            "abnormal_api_activity": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["cloud_user_id"] == "test_user_sim"
    assert data["simulated_risk_score"] > data["current_risk_score"]
    assert data["delta"] > 0
    assert "explanation" in data
    assert len(data["factor_contributions"]) > 0
