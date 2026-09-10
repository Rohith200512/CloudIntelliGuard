"""Unit tests for feature engineering service."""
import pandas as pd
import pytest
from datetime import datetime, timezone

from app.services.feature_engineering import (
    extract_raw_features,
    extract_derived_features,
    build_user_feature_vector,
    SENSITIVE_SERVICES,
)


@pytest.fixture
def sample_df():
    now = datetime.now(timezone.utc)
    return pd.DataFrame([
        {"cloud_user_id": "U001", "action": "listbuckets", "service": "s3",
         "resource": "arn:aws:s3:::bucket", "status": "success",
         "timestamp": pd.Timestamp("2024-01-15T08:00:00Z")},
        {"cloud_user_id": "U001", "action": "getobject", "service": "s3",
         "resource": "arn:aws:s3:::bucket/file.txt", "status": "success",
         "timestamp": pd.Timestamp("2024-01-15T09:00:00Z")},
        {"cloud_user_id": "U002", "action": "getuser", "service": "iam",
         "resource": "arn:aws:iam::123:user/admin", "status": "failure",
         "timestamp": pd.Timestamp("2024-01-15T02:00:00Z")},
        {"cloud_user_id": "U002", "action": "getsecretvalue", "service": "secretsmanager",
         "resource": "arn:aws:secretsmanager:us-east-1:123:secret/db-pass", "status": "success",
         "timestamp": pd.Timestamp("2024-01-15T02:05:00Z")},
    ])


def test_extract_raw_features_known_user(sample_df):
    raw = extract_raw_features(sample_df, "U001")
    assert raw["event_count"] == 2
    assert raw["unique_services"] == 1
    assert "s3" in raw["services"]
    assert raw["failure_count"] == 0


def test_extract_raw_features_unknown_user(sample_df):
    raw = extract_raw_features(sample_df, "UNKNOWN")
    assert raw["event_count"] == 0


def test_extract_derived_features_sensitive(sample_df):
    derived = extract_derived_features(sample_df, "U002")
    assert derived["accessed_sensitive_service"] is True
    assert len(derived["sensitive_services_accessed"]) >= 1
    assert derived["failed_ratio"] == 0.5


def test_extract_derived_features_failed_ratio(sample_df):
    derived = extract_derived_features(sample_df, "U001")
    assert derived["failed_ratio"] == 0.0


def test_build_user_feature_vector_length():
    raw = {"event_count": 10, "unique_services": 2, "unique_actions": 3, "unique_resources": 5, "unique_source_ips": 1, "services": ["s3"]}
    derived = {"request_frequency_per_hour": 5.0, "failed_ratio": 0.1, "action_diversity": 0.3,
               "mean_hour_of_day": 10.0, "recent_intensity": 0.2, "accessed_sensitive_service": False,
               "sensitive_resources_count": 0, "affected_resources_count": 5,
               "first_time_services": [], "first_time_resources": [], "historical_avg_daily_requests": 8.0}
    vec = build_user_feature_vector(raw, derived, feature_dim=16)
    assert len(vec) == 16
    assert all(isinstance(v, float) for v in vec)


def test_build_user_feature_vector_all_none():
    vec = build_user_feature_vector({}, {}, feature_dim=16)
    assert len(vec) == 16
    assert all(v == 0.0 for v in vec)
