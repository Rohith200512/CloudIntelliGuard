"""
Feature engineering service — CloudIntelliGuard.

Computes per-user RAW and DERIVED features from a window DataFrame.

RAW FEATURES:    Directly observed from the event log (no fabrication).
DERIVED FEATURES: Computed aggregations/statistics over observed data.

No information is fabricated. All features are computed from what is present.
Missing data is handled with None/NaN rather than imputed values.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

# Services considered sensitive for risk assessment
SENSITIVE_SERVICES: Set[str] = {
    "iam", "sts", "secretsmanager", "kms", "cloudtrail",
    "secrets manager", "certificate manager",
}

SENSITIVE_RESOURCES_PATTERNS: List[str] = [
    "secret", "key", "password", "credential", "admin", "root", "policy",
]


def extract_raw_features(
    events_df: pd.DataFrame,
    cloud_user_id: str,
) -> Dict[str, Any]:
    """
    Extract RAW features for a user from raw event records.

    RAW features are directly observed — no statistical transformation.
    """
    user_df = events_df[events_df["cloud_user_id"] == cloud_user_id]

    if user_df.empty:
        return {"cloud_user_id": cloud_user_id, "event_count": 0}

    raw: Dict[str, Any] = {
        "cloud_user_id": cloud_user_id,
        # Counts
        "event_count": len(user_df),
        "unique_actions": int(user_df["action"].nunique()) if "action" in user_df.columns else None,
        "unique_services": int(user_df["service"].nunique()) if "service" in user_df.columns else None,
        "unique_resources": int(user_df["resource"].nunique()) if "resource" in user_df.columns else None,
        "unique_source_ips": int(user_df["source_ip"].nunique()) if "source_ip" in user_df.columns else None,
        # Lists
        "actions": list(user_df["action"].dropna().unique()) if "action" in user_df.columns else [],
        "services": list(user_df["service"].dropna().unique()) if "service" in user_df.columns else [],
        "resources": list(user_df["resource"].dropna().unique()) if "resource" in user_df.columns else [],
        # Status
        "success_count": int((user_df["status"].str.lower() == "success").sum()) if "status" in user_df.columns else None,
        "failure_count": int((user_df["status"].str.lower() == "failure").sum()) if "status" in user_df.columns else None,
        # Temporal
        "first_event_time": user_df["timestamp"].min().isoformat() if "timestamp" in user_df.columns else None,
        "last_event_time": user_df["timestamp"].max().isoformat() if "timestamp" in user_df.columns else None,
    }
    return raw


def extract_derived_features(
    events_df: pd.DataFrame,
    cloud_user_id: str,
    window_start: Optional[datetime] = None,
    window_end: Optional[datetime] = None,
    historical_events_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Extract DERIVED (computed) features for a user.

    DERIVED features are aggregations and statistics computed over observed data.
    Historical features require historical_events_df to be provided.
    If not provided, historical features are returned as None.
    """
    user_df = events_df[events_df["cloud_user_id"] == cloud_user_id].copy()

    if user_df.empty:
        return {"cloud_user_id": cloud_user_id, "event_count": 0}

    user_df["timestamp"] = pd.to_datetime(user_df["timestamp"], utc=True)

    derived: Dict[str, Any] = {
        "cloud_user_id": cloud_user_id,
    }

    # Request frequency (events per hour in window)
    if window_start and window_end:
        window_hours = max(
            (window_end - window_start).total_seconds() / 3600, 0.001
        )
        derived["request_frequency_per_hour"] = len(user_df) / window_hours
    else:
        derived["request_frequency_per_hour"] = None

    # Action frequency (unique actions / total events)
    if "action" in user_df.columns and len(user_df) > 0:
        derived["action_diversity"] = user_df["action"].nunique() / len(user_df)
        derived["most_common_action"] = user_df["action"].mode().iloc[0] if not user_df["action"].isna().all() else None
    else:
        derived["action_diversity"] = None
        derived["most_common_action"] = None

    # Service frequency
    if "service" in user_df.columns:
        derived["service_count"] = int(user_df["service"].nunique())
        svc_counts = user_df["service"].value_counts()
        derived["most_common_service"] = svc_counts.index[0] if not svc_counts.empty else None
    else:
        derived["service_count"] = None
        derived["most_common_service"] = None

    # Time-of-day (hour of day, mean)
    if "timestamp" in user_df.columns:
        derived["mean_hour_of_day"] = float(user_df["timestamp"].dt.hour.mean())
        derived["day_of_week_counts"] = user_df["timestamp"].dt.dayofweek.value_counts().to_dict()

    # Failed request ratio
    if "status" in user_df.columns:
        total = len(user_df)
        failures = int((user_df["status"].str.lower() == "failure").sum())
        derived["failed_ratio"] = failures / total if total > 0 else 0.0
        derived["failed_count"] = failures
    else:
        derived["failed_ratio"] = None
        derived["failed_count"] = None

    # Sensitive service access
    if "service" in user_df.columns:
        user_services = set(user_df["service"].dropna().str.lower())
        sensitive_accessed = user_services & SENSITIVE_SERVICES
        derived["sensitive_services_accessed"] = list(sensitive_accessed)
        derived["accessed_sensitive_service"] = len(sensitive_accessed) > 0
    else:
        derived["sensitive_services_accessed"] = []
        derived["accessed_sensitive_service"] = False

    # Sensitive resource access
    if "resource" in user_df.columns:
        resources = user_df["resource"].dropna().str.lower()
        sensitive_resources = [
            r for r in resources
            if any(pattern in r for pattern in SENSITIVE_RESOURCES_PATTERNS)
        ]
        derived["sensitive_resources_count"] = len(sensitive_resources)
        derived["sensitive_resources"] = list(set(sensitive_resources))
    else:
        derived["sensitive_resources_count"] = 0
        derived["sensitive_resources"] = []

    # Affected resources count
    derived["affected_resources_count"] = (
        int(user_df["resource"].nunique()) if "resource" in user_df.columns else 0
    )

    # Recent activity intensity (events in last 20% of window)
    if window_start and window_end and "timestamp" in user_df.columns:
        window_duration = (window_end - window_start).total_seconds()
        recent_cutoff = window_start.timestamp() + 0.8 * window_duration
        recent_df = user_df[user_df["timestamp"].apply(lambda x: x.timestamp()) >= recent_cutoff]
        derived["recent_intensity"] = len(recent_df) / max(len(user_df), 1)
    else:
        derived["recent_intensity"] = None

    # Historical features (requires historical data)
    if historical_events_df is not None and not historical_events_df.empty:
        hist_user = historical_events_df[
            historical_events_df["cloud_user_id"] == cloud_user_id
        ]
        if not hist_user.empty:
            hist_services = set(hist_user["service"].dropna().str.lower()) if "service" in hist_user.columns else set()
            current_services = set(user_df["service"].dropna().str.lower()) if "service" in user_df.columns else set()
            first_time_services = list(current_services - hist_services)
            derived["first_time_services"] = first_time_services

            hist_resources = set(hist_user["resource"].dropna().str.lower()) if "resource" in hist_user.columns else set()
            current_resources = set(user_df["resource"].dropna().str.lower()) if "resource" in user_df.columns else set()
            first_time_resources = list(current_resources - hist_resources)
            derived["first_time_resources"] = first_time_resources

            # Historical average request count
            # Compute by grouping historical by day
            if "timestamp" in hist_user.columns:
                hist_user = hist_user.copy()
                hist_user["timestamp"] = pd.to_datetime(hist_user["timestamp"], utc=True)
                daily_counts = hist_user.groupby(hist_user["timestamp"].dt.date).size()
                derived["historical_avg_daily_requests"] = float(daily_counts.mean())
            else:
                derived["historical_avg_daily_requests"] = None
        else:
            derived["first_time_services"] = list(
                user_df["service"].dropna().unique() if "service" in user_df.columns else []
            )
            derived["first_time_resources"] = list(
                user_df["resource"].dropna().unique() if "resource" in user_df.columns else []
            )
            derived["historical_avg_daily_requests"] = None
    else:
        derived["first_time_services"] = None
        derived["first_time_resources"] = None
        derived["historical_avg_daily_requests"] = None

    return derived


def build_user_feature_vector(
    raw_features: Dict[str, Any],
    derived_features: Dict[str, Any],
    feature_dim: int = 16,
) -> List[float]:
    """
    Build a fixed-length numeric feature vector for a user node.

    This vector is used as input to the GNN node features.
    Features are normalized to [0, 1] where applicable.

    Returns a list of floats of length `feature_dim`.
    Missing values are represented as 0.0.
    """
    def safe_float(val: Any, default: float = 0.0) -> float:
        try:
            if val is None or (isinstance(val, float) and np.isnan(val)):
                return default
            return float(val)
        except (TypeError, ValueError):
            return default

    vec = [
        safe_float(raw_features.get("event_count", 0)) / 1000.0,  # normalized
        safe_float(raw_features.get("unique_actions")),
        safe_float(raw_features.get("unique_services")),
        safe_float(raw_features.get("unique_resources")),
        safe_float(derived_features.get("request_frequency_per_hour", 0)) / 100.0,
        safe_float(derived_features.get("failed_ratio", 0)),
        safe_float(derived_features.get("action_diversity", 0)),
        safe_float(derived_features.get("mean_hour_of_day", 0)) / 24.0,
        safe_float(derived_features.get("recent_intensity", 0)),
        1.0 if derived_features.get("accessed_sensitive_service") else 0.0,
        safe_float(derived_features.get("sensitive_resources_count", 0)) / 10.0,
        safe_float(derived_features.get("affected_resources_count", 0)) / 50.0,
        safe_float(len(derived_features.get("first_time_services") or [])) / 10.0,
        safe_float(len(derived_features.get("first_time_resources") or [])) / 20.0,
        safe_float(derived_features.get("historical_avg_daily_requests", 0)) / 100.0,
        safe_float(raw_features.get("unique_source_ips")),
    ]

    # Pad or trim to exactly feature_dim
    if len(vec) < feature_dim:
        vec.extend([0.0] * (feature_dim - len(vec)))
    return vec[:feature_dim]
