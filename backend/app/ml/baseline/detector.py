"""
Anomaly detector on top of baseline GCN embeddings.

Uses Isolation Forest for anomaly scoring.
Thresholds are configurable — a single universal threshold is NOT assumed optimal.
Scores are normalized to [0, 1] (1 = most anomalous).
"""
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


@dataclass
class ThresholdConfig:
    method: str = "statistical"     # statistical | adaptive | fixed
    statistical_n_sigma: float = 2.0
    fixed_threshold: Optional[float] = None
    contamination: float = 0.1

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "statistical_n_sigma": self.statistical_n_sigma,
            "fixed_threshold": self.fixed_threshold,
            "contamination": self.contamination,
        }


class BaselineAnomalyDetector:
    """
    Isolation Forest anomaly scorer over node embeddings.

    Fitted on training window embeddings (assumed mostly normal).
    At inference time, scores deviation from the learned distribution.
    """

    def __init__(self, threshold_config: Optional[ThresholdConfig] = None):
        self.threshold_config = threshold_config or ThresholdConfig()
        self.isolation_forest: Optional[IsolationForest] = None
        self.scaler = StandardScaler()
        self.fitted = False
        self.threshold_value: Optional[float] = None
        self.train_score_mean: Optional[float] = None
        self.train_score_std: Optional[float] = None

    def fit(self, embeddings: np.ndarray) -> None:
        if len(embeddings) < 2:
            raise ValueError("Need at least 2 samples to fit the anomaly detector.")

        scaled = self.scaler.fit_transform(embeddings)
        self.isolation_forest = IsolationForest(
            contamination=self.threshold_config.contamination,
            random_state=42,
            n_estimators=100,
        )
        self.isolation_forest.fit(scaled)

        raw = self.isolation_forest.decision_function(scaled)
        scores = self._normalize(-raw)
        self.train_score_mean = float(np.mean(scores))
        self.train_score_std = float(np.std(scores))
        self.threshold_value = self._compute_threshold(scores)
        self.fitted = True

    def _normalize(self, raw: np.ndarray) -> np.ndarray:
        lo, hi = raw.min(), raw.max()
        if hi - lo < 1e-10:
            return np.zeros_like(raw)
        return (raw - lo) / (hi - lo)

    def _compute_threshold(self, train_scores: np.ndarray) -> float:
        cfg = self.threshold_config
        if cfg.method == "fixed" and cfg.fixed_threshold is not None:
            return cfg.fixed_threshold
        if cfg.method == "statistical":
            return min(1.0, float(np.mean(train_scores)) + cfg.statistical_n_sigma * float(np.std(train_scores)))
        return 0.5

    def predict(self, embeddings: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if not self.fitted:
            raise RuntimeError("Detector not fitted. Call fit() first.")
        scaled = self.scaler.transform(embeddings)
        raw = self.isolation_forest.decision_function(scaled)
        scores = self._normalize(-raw)
        is_anomaly = scores >= self.threshold_value
        return scores, is_anomaly

    def get_threshold_info(self) -> dict:
        return {
            "threshold_value": self.threshold_value,
            "threshold_type": self.threshold_config.method,
            "train_score_mean": self.train_score_mean,
            "train_score_std": self.train_score_std,
            **self.threshold_config.to_dict(),
        }
