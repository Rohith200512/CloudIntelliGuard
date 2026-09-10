"""
Explainability Module — CloudIntelliGuard.

Phase 1: Rule-based heuristic explanations (observational, not causal).
Future: GNNExplainer integration stub is present but not yet deployed.

IMPORTANT: Explanations describe what was detected in the data.
They are NOT claimed to be mathematically causal explanations.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExplanationFinding:
    category: str
    finding: str
    evidence: Optional[Any] = None
    severity: str = "INFO"  # INFO | WARNING | HIGH


@dataclass
class AnomalyExplanation:
    cloud_user_id: str
    summary: str
    findings: List[ExplanationFinding]
    explanation_method: str  # rule_based | gnnexplainer (future)
    is_causal: bool = False
    causal_note: str = "Explanations are observational, not mathematically causal."

    def to_dict(self) -> dict:
        return {
            "cloud_user_id": self.cloud_user_id,
            "summary": self.summary,
            "findings": [
                {"category": f.category, "finding": f.finding,
                 "severity": f.severity, "evidence": f.evidence}
                for f in self.findings
            ],
            "explanation_method": self.explanation_method,
            "is_causal": self.is_causal,
            "causal_note": self.causal_note,
        }


def explain_anomaly(
    cloud_user_id: str,
    anomaly_score: float,
    is_anomaly: bool,
    event_count: int,
    failed_request_count: int,
    unique_services: List[str],
    unusual_services: List[str],
    sensitive_resources: List[str],
    new_resources: List[str],
    historical_avg_requests: Optional[float] = None,
    temporal_anomaly: bool = False,
    is_coordinated: bool = False,
) -> AnomalyExplanation:
    """Generate rule-based human-readable explanation for an anomaly detection."""
    findings: List[ExplanationFinding] = []

    if unusual_services:
        findings.append(ExplanationFinding(
            category="service_access",
            finding=f"Accessed {len(unusual_services)} unusual service(s) not in historical baseline: {', '.join(unusual_services[:5])}",
            evidence=unusual_services,
            severity="HIGH" if len(unusual_services) >= 3 else "WARNING",
        ))

    if sensitive_resources:
        findings.append(ExplanationFinding(
            category="resource_access",
            finding=f"Accessed {len(sensitive_resources)} sensitive resource(s)",
            evidence=sensitive_resources,
            severity="HIGH",
        ))

    if new_resources:
        findings.append(ExplanationFinding(
            category="resource_access",
            finding=f"First-time access to {len(new_resources)} resource(s): {', '.join(new_resources[:3])}",
            evidence=new_resources,
            severity="WARNING",
        ))

    if failed_request_count > 0 and event_count > 0:
        pct = failed_request_count / event_count * 100
        findings.append(ExplanationFinding(
            category="request_pattern",
            finding=f"{failed_request_count} failed API calls ({pct:.1f}% failure rate)",
            evidence={"failed": failed_request_count, "total": event_count},
            severity="HIGH" if pct >= 50 else "WARNING",
        ))

    if historical_avg_requests is not None and historical_avg_requests > 0:
        dev = (event_count - historical_avg_requests) / historical_avg_requests
        if abs(dev) > 0.5:
            findings.append(ExplanationFinding(
                category="request_pattern",
                finding=f"Request count ({event_count}) deviates {dev:+.0%} from historical avg ({historical_avg_requests:.0f})",
                evidence={"current": event_count, "historical_avg": historical_avg_requests},
                severity="HIGH" if abs(dev) >= 1.0 else "WARNING",
            ))

    if temporal_anomaly:
        findings.append(ExplanationFinding(
            category="temporal",
            finding="Activity detected at unusual time-of-day or day-of-week relative to historical pattern",
            severity="WARNING",
        ))

    if is_coordinated:
        findings.append(ExplanationFinding(
            category="coordinated",
            finding="Activity overlaps with other anomalous users (shared services, resources, or timing)",
            severity="HIGH",
        ))

    if anomaly_score > 0.8:
        findings.append(ExplanationFinding(
            category="ml_signal",
            finding=f"High ML anomaly score ({anomaly_score:.3f}) — significant behavioral deviation from modeled normal patterns",
            evidence={"anomaly_score": anomaly_score},
            severity="HIGH",
        ))
    elif anomaly_score > 0.5:
        findings.append(ExplanationFinding(
            category="ml_signal",
            finding=f"Moderate ML anomaly score ({anomaly_score:.3f})",
            severity="WARNING",
        ))

    if not findings:
        findings.append(ExplanationFinding(
            category="ml_signal",
            finding=f"Anomaly score {anomaly_score:.3f} exceeded threshold but no specific behavioral indicator found.",
            severity="INFO",
        ))

    if is_anomaly:
        high = [f for f in findings if f.severity == "HIGH"]
        summary = f"ANOMALY: {high[0].finding}" if high else f"ANOMALY: Behavioral deviation (score {anomaly_score:.3f})"
    else:
        summary = f"No significant anomaly (score {anomaly_score:.3f})"

    return AnomalyExplanation(
        cloud_user_id=cloud_user_id,
        summary=summary,
        findings=findings,
        explanation_method="rule_based",
    )


def explain_with_gnn(
    cloud_user_id: str,
    model: Any,
    node_features: Any,
    edge_index: Any,
    target_node_idx: int,
) -> Dict[str, Any]:
    """
    GNNExplainer integration stub — NOT YET IMPLEMENTED in Phase 1.

    When implemented, this will return node/edge importance scores.
    Integration point:
        from torch_geometric.explain import GNNExplainer
        explainer = GNNExplainer(model, epochs=200, return_type='raw')
        node_feat_mask, edge_mask = explainer.explain_node(
            target_node_idx, node_features, edge_index
        )
    """
    return {
        "status": "not_implemented",
        "message": "GNNExplainer integration is prepared but not deployed in Phase 1.",
        "cloud_user_id": cloud_user_id,
        "note": "Rule-based explanations are used instead.",
    }
