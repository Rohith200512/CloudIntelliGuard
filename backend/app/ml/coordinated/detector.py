"""
Coordinated Anomaly Detection — CloudIntelliGuard.

Detects suspicious behavior that appears coordinated across multiple cloud users.
Uses heuristic pairwise similarity across: shared services, shared resources,
similar action sequences, temporal proximity.

NOTE:
  - No attack labels are invented.
  - Only factual behavioral evidence is returned.
  - Thresholds are configurable.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

import numpy as np


@dataclass
class CoordinationConfig:
    min_users: int = 2
    min_coordination_score: float = 0.4
    shared_service_weight: float = 0.30
    shared_resource_weight: float = 0.25
    temporal_proximity_weight: float = 0.25
    similar_action_weight: float = 0.20
    temporal_window_seconds: int = 300


@dataclass
class UserActivitySummary:
    cloud_user_id: str
    anomaly_score: float
    is_anomaly: bool
    services_accessed: List[str]
    resources_accessed: List[str]
    actions_performed: List[str]
    event_timestamps: List[datetime]
    failed_count: int = 0


@dataclass
class CoordinatedEventResult:
    coordination_score: float
    related_cloud_user_ids: List[str]
    related_services: List[str]
    related_resources: List[str]
    time_window_start: Optional[datetime]
    time_window_end: Optional[datetime]
    evidence: Dict
    threshold_used: float


def detect_coordinated_anomalies(
    user_summaries: List[UserActivitySummary],
    config: Optional[CoordinationConfig] = None,
    window_start: Optional[datetime] = None,
    window_end: Optional[datetime] = None,
) -> List[CoordinatedEventResult]:
    """
    Detect coordinated suspicious behavior across anomalous users.

    Only anomalous users are considered. Pairwise similarity is computed
    across service, resource, action, and temporal dimensions.
    Greedy clustering groups users with similarity above the threshold.
    """
    if config is None:
        config = CoordinationConfig()

    anomalous = [u for u in user_summaries if u.is_anomaly]
    if len(anomalous) < config.min_users:
        return []

    n = len(anomalous)
    sim = np.zeros((n, n))

    for i in range(n):
        for j in range(i + 1, n):
            s = _pair_similarity(anomalous[i], anomalous[j], config)
            sim[i][j] = s
            sim[j][i] = s

    visited: Set[int] = set()
    clusters: List[List[int]] = []

    for i in range(n):
        if i in visited:
            continue
        cluster = [i]
        visited.add(i)
        for j in range(n):
            if j not in visited and sim[i][j] >= config.min_coordination_score:
                cluster.append(j)
                visited.add(j)
        if len(cluster) >= config.min_users:
            clusters.append(cluster)

    return [
        _build_result(
            [anomalous[i] for i in cluster],
            sim, cluster, config, window_start, window_end
        )
        for cluster in clusters
    ]


def _pair_similarity(u1: UserActivitySummary, u2: UserActivitySummary, cfg: CoordinationConfig) -> float:
    s1, s2 = set(u1.services_accessed), set(u2.services_accessed)
    r1, r2 = set(u1.resources_accessed), set(u2.resources_accessed)
    a1, a2 = set(u1.actions_performed), set(u2.actions_performed)
    return (
        cfg.shared_service_weight * _jaccard(s1, s2)
        + cfg.shared_resource_weight * _jaccard(r1, r2)
        + cfg.similar_action_weight * _jaccard(a1, a2)
        + cfg.temporal_proximity_weight * _temporal_score(
            u1.event_timestamps, u2.event_timestamps, cfg.temporal_window_seconds
        )
    )


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def _temporal_score(ts1: List[datetime], ts2: List[datetime], window_s: int) -> float:
    if not ts1 or not ts2:
        return 0.0
    close = sum(
        1 for t1 in ts1
        if any(abs((t1 - t2).total_seconds()) <= window_s for t2 in ts2)
    )
    return close / len(ts1)


def _build_result(
    users: List[UserActivitySummary],
    sim: np.ndarray,
    indices: List[int],
    cfg: CoordinationConfig,
    window_start: Optional[datetime],
    window_end: Optional[datetime],
) -> CoordinatedEventResult:
    all_services: Set[str] = set()
    all_resources: Set[str] = set()
    for u in users:
        all_services.update(u.services_accessed)
        all_resources.update(u.resources_accessed)

    shared_services = list(set.intersection(*[set(u.services_accessed) for u in users])) if users else []
    shared_resources = list(set.intersection(*[set(u.resources_accessed) for u in users])) if users else []

    pair_scores = [sim[indices[i]][indices[j]] for i in range(len(indices)) for j in range(i+1, len(indices))]
    avg_score = float(np.mean(pair_scores)) if pair_scores else 0.0

    return CoordinatedEventResult(
        coordination_score=round(avg_score, 4),
        related_cloud_user_ids=[u.cloud_user_id for u in users],
        related_services=list(all_services),
        related_resources=list(all_resources),
        time_window_start=window_start,
        time_window_end=window_end,
        evidence={
            "shared_services": shared_services,
            "shared_resources": shared_resources,
            "user_anomaly_scores": {u.cloud_user_id: u.anomaly_score for u in users},
            "pairwise_similarity_mean": avg_score,
            "evidence_note": "Factual behavioral overlap only. Purely observational.",
        },
        threshold_used=cfg.min_coordination_score,
    )
