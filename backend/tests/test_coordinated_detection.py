"""Unit tests for coordinated anomaly detection."""
import pytest
from datetime import datetime, timezone

from app.ml.coordinated.detector import (
    CoordinationConfig,
    UserActivitySummary,
    detect_coordinated_anomalies,
)


def make_user(uid, is_anomaly, services, resources, actions, n_timestamps=5):
    from datetime import timedelta
    base = datetime(2024, 1, 15, 2, 0, 0, tzinfo=timezone.utc)
    timestamps = [base + timedelta(minutes=i * 3) for i in range(n_timestamps)]
    return UserActivitySummary(
        cloud_user_id=uid,
        anomaly_score=0.8 if is_anomaly else 0.1,
        is_anomaly=is_anomaly,
        services_accessed=services,
        resources_accessed=resources,
        actions_performed=actions,
        event_timestamps=timestamps,
    )


def test_no_coordinated_with_single_anomalous_user():
    users = [
        make_user("U001", True, ["iam", "s3"], ["res1"], ["CreateKey"]),
        make_user("U002", False, ["ec2"], ["res2"], ["DescribeInstances"]),
    ]
    results = detect_coordinated_anomalies(users)
    assert results == []


def test_coordinated_detected_with_overlap():
    users = [
        make_user("U006", True, ["iam", "secretsmanager", "kms"], ["secret/db", "key/abc"], ["CreateAccessKey", "GetSecretValue"]),
        make_user("U007", True, ["iam", "secretsmanager", "s3"], ["secret/db", "bucket/x"], ["ListUsers", "GetSecretValue"]),
    ]
    cfg = CoordinationConfig(min_users=2, min_coordination_score=0.2)
    results = detect_coordinated_anomalies(users, cfg)
    assert len(results) >= 1
    result = results[0]
    assert "U006" in result.related_cloud_user_ids
    assert "U007" in result.related_cloud_user_ids


def test_no_coordination_when_all_normal():
    users = [
        make_user("U001", False, ["s3"], ["bucket"], ["GetObject"]),
        make_user("U002", False, ["ec2"], ["instance"], ["Describe"]),
    ]
    results = detect_coordinated_anomalies(users)
    assert results == []


def test_coordination_score_in_range():
    users = [
        make_user("U006", True, ["iam", "kms"], ["key/a"], ["Decrypt"]),
        make_user("U007", True, ["iam", "kms"], ["key/a"], ["Decrypt"]),
    ]
    cfg = CoordinationConfig(min_users=2, min_coordination_score=0.1)
    results = detect_coordinated_anomalies(users, cfg)
    for r in results:
        assert 0.0 <= r.coordination_score <= 1.0


def test_evidence_has_no_attack_labels():
    users = [
        make_user("U006", True, ["iam"], ["arn:iam::123:user/admin"], ["CreateAccessKey"]),
        make_user("U007", True, ["iam"], ["arn:iam::123:user/admin"], ["CreateAccessKey"]),
    ]
    cfg = CoordinationConfig(min_users=2, min_coordination_score=0.1)
    results = detect_coordinated_anomalies(users, cfg)
    for r in results:
        evidence_str = str(r.evidence)
        for bad_label in ["exfiltration", "privilege escalation", "attack"]:
            assert bad_label not in evidence_str.lower()
