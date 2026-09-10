"""
Evaluation metrics — CloudIntelliGuard.

Metrics are ONLY computed when ground-truth labels are provided.
If no ground truth exists, results are clearly returned as 'not evaluated'.
No fake metrics are ever returned.
"""
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

import numpy as np

try:
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score,
        f1_score, roc_auc_score, confusion_matrix,
    )
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


@dataclass
class EvaluationMetrics:
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1: Optional[float] = None
    roc_auc: Optional[float] = None
    false_positive_rate: Optional[float] = None
    detection_latency_ms: Optional[float] = None
    total_runtime_s: Optional[float] = None
    evaluated_on_ground_truth: bool = False
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1,
            "roc_auc": self.roc_auc,
            "false_positive_rate": self.false_positive_rate,
            "detection_latency_ms": self.detection_latency_ms,
            "total_runtime_s": self.total_runtime_s,
            "evaluated_on_ground_truth": self.evaluated_on_ground_truth,
            "notes": self.notes,
        }


def compute_metrics(
    y_true: List[int],
    y_pred: List[int],
    y_score: Optional[List[float]] = None,
    detection_latency_ms: Optional[float] = None,
    total_runtime_s: Optional[float] = None,
) -> EvaluationMetrics:
    """Compute classification metrics against ground-truth labels."""
    if not SKLEARN_AVAILABLE:
        return EvaluationMetrics(
            notes="scikit-learn not available.",
            evaluated_on_ground_truth=False,
        )

    yt = np.array(y_true)
    yp = np.array(y_pred)

    fpr = None
    if len(np.unique(yt)) > 1:
        cm = confusion_matrix(yt, yp, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel()
        fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else None
    else:
        fpr = None

    roc_auc = None
    if y_score is not None and len(np.unique(yt)) > 1:
        try:
            roc_auc = float(roc_auc_score(yt, np.array(y_score)))
        except Exception:
            roc_auc = None

    return EvaluationMetrics(
        accuracy=float(accuracy_score(yt, yp)),
        precision=float(precision_score(yt, yp, zero_division=0)),
        recall=float(recall_score(yt, yp, zero_division=0)),
        f1=float(f1_score(yt, yp, zero_division=0)),
        roc_auc=roc_auc,
        false_positive_rate=fpr,
        detection_latency_ms=detection_latency_ms,
        total_runtime_s=total_runtime_s,
        evaluated_on_ground_truth=True,
    )


def not_evaluated_metrics(reason: str) -> EvaluationMetrics:
    """Return a clearly-labeled 'not evaluated' placeholder."""
    return EvaluationMetrics(
        evaluated_on_ground_truth=False,
        notes=f"NOT EVALUATED: {reason}",
    )
