"""
Early-Warning Risk Prediction — CloudIntelliGuard.

Architecture is implemented. Prediction returns `prediction_available=False`
when insufficient historical data exists rather than fabricating predictions.

Minimum requirement: 3 historical data points.
Method: Linear regression over historical risk scores (transparent, explainable).
"""
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

MIN_HISTORY_POINTS = 3


@dataclass
class EarlyWarningResult:
    cloud_user_id: str
    current_risk: float
    historical_trend: Optional[List[float]]
    predicted_next_risk: Optional[float]
    trend_direction: Optional[str]  # INCREASING | STABLE | DECREASING
    prediction_available: bool
    unavailability_reason: Optional[str]

    def to_dict(self) -> dict:
        return {
            "cloud_user_id": self.cloud_user_id,
            "current_risk": self.current_risk,
            "historical_trend": self.historical_trend,
            "predicted_next_risk": self.predicted_next_risk,
            "trend_direction": self.trend_direction,
            "prediction_available": self.prediction_available,
            "unavailability_reason": self.unavailability_reason,
        }


def predict_user_risk(
    cloud_user_id: str,
    current_risk: float,
    historical_risks: List[float],
    increasing_threshold: float = 5.0,
    decreasing_threshold: float = -5.0,
) -> EarlyWarningResult:
    """
    Generate early-warning risk prediction for a user.

    If < MIN_HISTORY_POINTS data points exist, returns prediction_available=False.
    Otherwise uses linear regression to predict the next window's risk score.

    NOTE: This is a simple, transparent method.
    A more sophisticated model (e.g. LSTM) can replace it in a later phase.
    """
    all_scores = historical_risks + [current_risk]

    if len(all_scores) < MIN_HISTORY_POINTS:
        return EarlyWarningResult(
            cloud_user_id=cloud_user_id,
            current_risk=current_risk,
            historical_trend=historical_risks or None,
            predicted_next_risk=None,
            trend_direction=None,
            prediction_available=False,
            unavailability_reason=(
                f"Insufficient historical data. "
                f"Need {MIN_HISTORY_POINTS} points, have {len(all_scores)}."
            ),
        )

    x = np.arange(len(all_scores), dtype=float)
    y = np.array(all_scores, dtype=float)
    slope, intercept = np.polyfit(x, y, 1)

    predicted = float(np.clip(intercept + slope * len(all_scores), 0.0, 100.0))

    if slope > increasing_threshold:
        direction = "INCREASING"
    elif slope < decreasing_threshold:
        direction = "DECREASING"
    else:
        direction = "STABLE"

    return EarlyWarningResult(
        cloud_user_id=cloud_user_id,
        current_risk=current_risk,
        historical_trend=historical_risks,
        predicted_next_risk=round(predicted, 2),
        trend_direction=direction,
        prediction_available=True,
        unavailability_reason=None,
    )
