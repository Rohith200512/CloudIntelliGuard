"""Unit tests for risk scoring module."""
import pytest
from app.ml.risk.scorer import compute_risk_score, FACTOR_MAX_CONTRIBUTIONS


def test_basic_risk_score_low():
    score, level, factors = compute_risk_score(
        anomaly_score=0.1,
        is_anomaly=False,
        event_count=10,
        failed_request_count=0,
        unique_services=["s3"],
        unusual_services=[],
        sensitive_resources=[],
    )
    assert 0.0 <= score <= 100.0
    assert level == "LOW"


def test_basic_risk_score_high():
    score, level, factors = compute_risk_score(
        anomaly_score=0.9,
        is_anomaly=True,
        event_count=200,
        failed_request_count=80,
        unique_services=["iam", "secretsmanager", "kms"],
        unusual_services=["iam", "secretsmanager"],
        sensitive_resources=["arn:aws:secretsmanager:::secret/db", "arn:aws:kms:::key/abc"],
        historical_avg_requests=20.0,
        recent_intensity=0.8,
        is_coordinated=True,
    )
    assert score > 50.0  # Should be HIGH or CRITICAL
    assert level in ("HIGH", "CRITICAL")


def test_score_is_deterministic():
    kwargs = dict(
        anomaly_score=0.6,
        is_anomaly=True,
        event_count=50,
        failed_request_count=10,
        unique_services=["iam"],
        unusual_services=["iam"],
        sensitive_resources=[],
    )
    s1, _, _ = compute_risk_score(**kwargs)
    s2, _, _ = compute_risk_score(**kwargs)
    assert s1 == s2


def test_score_range():
    for anomaly_score in [0.0, 0.5, 1.0]:
        score, _, _ = compute_risk_score(
            anomaly_score=anomaly_score,
            is_anomaly=anomaly_score >= 0.5,
            event_count=10,
            failed_request_count=0,
            unique_services=[],
            unusual_services=[],
            sensitive_resources=[],
        )
        assert 0.0 <= score <= 100.0


def test_factors_are_returned():
    _, _, factors = compute_risk_score(
        anomaly_score=0.8,
        is_anomaly=True,
        event_count=100,
        failed_request_count=20,
        unique_services=["iam"],
        unusual_services=["iam"],
        sensitive_resources=["secret/db"],
        is_coordinated=True,
    )
    assert len(factors) > 0
    factor_names = [f.factor for f in factors]
    assert any("Anomaly" in fn for fn in factor_names)


def test_coordinated_adds_contribution():
    _, _, factors_no_coord = compute_risk_score(
        anomaly_score=0.5, is_anomaly=True, event_count=10,
        failed_request_count=0, unique_services=[], unusual_services=[],
        sensitive_resources=[], is_coordinated=False,
    )
    _, _, factors_coord = compute_risk_score(
        anomaly_score=0.5, is_anomaly=True, event_count=10,
        failed_request_count=0, unique_services=[], unusual_services=[],
        sensitive_resources=[], is_coordinated=True,
    )
    coord_factors = [f.factor for f in factors_coord]
    assert any("Coordinated" in fn for fn in coord_factors)
