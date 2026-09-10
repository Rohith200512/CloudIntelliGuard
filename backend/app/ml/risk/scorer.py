"""
Context-Aware Risk Scoring — CloudIntelliGuard.

Combines evidence dimensions into a composite risk score (0–100).
Factor weights and logic are fully documented below.

Risk Levels:
  0–24  : LOW
  25–49 : MEDIUM
  50–74 : HIGH
  75+   : CRITICAL
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

FACTOR_MAX_CONTRIBUTIONS: Dict[str, float] = {
    "anomaly_score":            30.0,
    "behavioral_deviation":     15.0,
    "unusual_service_access":   15.0,
    "sensitive_resource_access": 10.0,
    "failed_request_ratio":     10.0,
    "request_frequency":         8.0,
    "coordinated_behavior":      7.0,
    "temporal_anomaly":          5.0,
}

RISK_LEVELS = [
    ("CRITICAL", 75),
    ("HIGH",     50),
    ("MEDIUM",   25),
    ("LOW",       0),
]


@dataclass
class RiskFactorResult:
    factor: str
    contribution: float
    description: str
    raw_value: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "factor": self.factor,
            "contribution": round(self.contribution, 2),
            "description": self.description,
        }


def compute_risk_score(
    anomaly_score: float,
    is_anomaly: bool,
    event_count: int,
    failed_request_count: int,
    unique_services: List[str],
    unusual_services: List[str],
    sensitive_resources: List[str],
    historical_avg_requests: Optional[float] = None,
    recent_intensity: Optional[float] = None,
    is_coordinated: bool = False,
    temporal_anomaly_score: Optional[float] = None,
) -> Tuple[float, str, List[RiskFactorResult]]:
    """
    Compute context-aware risk score.

    All inputs are derived from real observed data or ML outputs.
    No random numbers are used. The function is deterministic.

    Returns:
        (risk_score: float 0–100, risk_level: str, factors: list)
    """
    factors: List[RiskFactorResult] = []
    total = 0.0

    # 1. Anomaly score (0–30)
    contrib = anomaly_score * FACTOR_MAX_CONTRIBUTIONS["anomaly_score"]
    if is_anomaly:
        contrib = min(FACTOR_MAX_CONTRIBUTIONS["anomaly_score"], contrib * 1.2)
    factors.append(RiskFactorResult(
        factor="Anomaly score",
        contribution=contrib,
        description=f"ML anomaly score {anomaly_score:.3f}" + (" (anomaly flagged)" if is_anomaly else ""),
        raw_value=anomaly_score,
    ))
    total += contrib

    # 2. Behavioral deviation (0–15)
    if historical_avg_requests is not None and historical_avg_requests > 0:
        dev = max(0.0, (event_count - historical_avg_requests) / historical_avg_requests)
        contrib = min(FACTOR_MAX_CONTRIBUTIONS["behavioral_deviation"], dev * 15.0)
        if contrib > 0.5:
            factors.append(RiskFactorResult(
                factor="Behavioral deviation",
                contribution=contrib,
                description=f"Requests {event_count} vs historical avg {historical_avg_requests:.0f}",
                raw_value=dev,
            ))
            total += contrib

    # 3. Unusual service access (0–15)
    if unusual_services and unique_services:
        ratio = len(unusual_services) / len(unique_services)
        contrib = ratio * FACTOR_MAX_CONTRIBUTIONS["unusual_service_access"]
        factors.append(RiskFactorResult(
            factor="Unusual service access",
            contribution=contrib,
            description=f"{len(unusual_services)} unusual service(s): {', '.join(unusual_services[:3])}",
            raw_value=ratio,
        ))
        total += contrib

    # 4. Sensitive resource access (0–10)
    if sensitive_resources:
        contrib = min(FACTOR_MAX_CONTRIBUTIONS["sensitive_resource_access"], len(sensitive_resources) * 3.0)
        factors.append(RiskFactorResult(
            factor="Sensitive resource access",
            contribution=contrib,
            description=f"{len(sensitive_resources)} sensitive resource(s) accessed",
            raw_value=float(len(sensitive_resources)),
        ))
        total += contrib

    # 5. Failed request ratio (0–10)
    if event_count > 0 and failed_request_count > 0:
        ratio = failed_request_count / event_count
        contrib = ratio * FACTOR_MAX_CONTRIBUTIONS["failed_request_ratio"]
        factors.append(RiskFactorResult(
            factor="Failed request ratio",
            contribution=contrib,
            description=f"{failed_request_count}/{event_count} requests failed ({ratio:.1%})",
            raw_value=ratio,
        ))
        total += contrib

    # 6. Elevated request frequency (0–8)
    if recent_intensity is not None and recent_intensity > 0.3:
        contrib = min(FACTOR_MAX_CONTRIBUTIONS["request_frequency"], recent_intensity * 8.0)
        factors.append(RiskFactorResult(
            factor="Elevated request frequency",
            contribution=contrib,
            description=f"Recent intensity: {recent_intensity:.2f}",
            raw_value=recent_intensity,
        ))
        total += contrib

    # 7. Coordinated behavior (0–7)
    if is_coordinated:
        contrib = FACTOR_MAX_CONTRIBUTIONS["coordinated_behavior"]
        factors.append(RiskFactorResult(
            factor="Coordinated behavior",
            contribution=contrib,
            description="Part of a detected coordinated suspicious activity group",
            raw_value=1.0,
        ))
        total += contrib

    # 8. Temporal anomaly (0–5)
    if temporal_anomaly_score is not None and temporal_anomaly_score > 0:
        contrib = temporal_anomaly_score * FACTOR_MAX_CONTRIBUTIONS["temporal_anomaly"]
        factors.append(RiskFactorResult(
            factor="Temporal anomaly",
            contribution=contrib,
            description=f"Unusual time-of-day/week pattern (score {temporal_anomaly_score:.2f})",
            raw_value=temporal_anomaly_score,
        ))
        total += contrib

    total = round(min(100.0, max(0.0, total)), 2)

    risk_level = "LOW"
    for level, threshold in RISK_LEVELS:
        if total >= threshold:
            risk_level = level
            break

    return total, risk_level, factors
