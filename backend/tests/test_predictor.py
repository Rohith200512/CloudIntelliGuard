"""Unit tests for early-warning predictor."""
import pytest
from app.ml.prediction.predictor import predict_user_risk, MIN_HISTORY_POINTS


def test_prediction_unavailable_when_insufficient_data():
    result = predict_user_risk(
        cloud_user_id="U001",
        current_risk=50.0,
        historical_risks=[40.0],  # only 2 total points (below MIN)
    )
    assert not result.prediction_available
    assert result.unavailability_reason is not None
    assert "Insufficient" in result.unavailability_reason
    assert result.predicted_next_risk is None
    assert result.trend_direction is None


def test_prediction_available_with_enough_data():
    result = predict_user_risk(
        cloud_user_id="U001",
        current_risk=70.0,
        historical_risks=[30.0, 50.0],  # 3 total points
    )
    assert result.prediction_available
    assert result.predicted_next_risk is not None
    assert 0.0 <= result.predicted_next_risk <= 100.0


def test_increasing_trend_detected():
    result = predict_user_risk(
        cloud_user_id="U001",
        current_risk=90.0,
        historical_risks=[10.0, 40.0, 70.0],
        increasing_threshold=5.0,
    )
    assert result.prediction_available
    assert result.trend_direction == "INCREASING"


def test_decreasing_trend_detected():
    result = predict_user_risk(
        cloud_user_id="U001",
        current_risk=10.0,
        historical_risks=[90.0, 60.0, 30.0],
        decreasing_threshold=-5.0,
    )
    assert result.prediction_available
    assert result.trend_direction == "DECREASING"


def test_result_is_deterministic():
    kwargs = dict(cloud_user_id="U001", current_risk=55.0, historical_risks=[30.0, 45.0])
    r1 = predict_user_risk(**kwargs)
    r2 = predict_user_risk(**kwargs)
    assert r1.predicted_next_risk == r2.predicted_next_risk


def test_prediction_clamped_to_valid_range():
    # Very steep slope — result should still be [0, 100]
    result = predict_user_risk(
        cloud_user_id="U001",
        current_risk=100.0,
        historical_risks=[50.0, 80.0],
    )
    if result.prediction_available:
        assert 0.0 <= result.predicted_next_risk <= 100.0
