"""Unit tests for adaptive window strategy."""
import pandas as pd
import pytest
from datetime import datetime, timezone

from app.ml.temporal.adaptive import (
    AdaptiveWindowConfig,
    select_adaptive_window,
    split_into_fixed_windows,
    split_into_adaptive_windows,
)


@pytest.fixture
def small_df():
    """10 events — LOW activity."""
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-15T00:00:00Z", periods=10, freq="30min", tz="UTC"),
        "cloud_user_id": ["U001"] * 10,
    })


@pytest.fixture
def large_df():
    """2000 events — HIGH activity."""
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-15T00:00:00Z", periods=2000, freq="1min", tz="UTC"),
        "cloud_user_id": ["U001"] * 2000,
    })


def test_low_activity_gives_long_window(small_df):
    cfg = AdaptiveWindowConfig(low_threshold=50, high_threshold=1000,
                                long_window_hours=48, default_window_hours=24, short_window_hours=6)
    result = select_adaptive_window(small_df, cfg)
    assert result.selected_window_hours == 48.0
    assert "LOW" in result.selection_rationale


def test_high_activity_gives_short_window(large_df):
    cfg = AdaptiveWindowConfig(low_threshold=50, high_threshold=1000,
                                long_window_hours=48, default_window_hours=24, short_window_hours=6)
    result = select_adaptive_window(large_df, cfg)
    assert result.selected_window_hours == 6.0
    assert "HIGH" in result.selection_rationale


def test_empty_dataframe_returns_default():
    result = select_adaptive_window(pd.DataFrame())
    assert result.event_count == 0
    assert result.selected_window_hours > 0


def test_fixed_window_split_creates_windows(small_df):
    windows = split_into_fixed_windows(small_df, window_hours=2)
    assert len(windows) > 0
    for df, start, end in windows:
        assert not df.empty
        assert start < end


def test_adaptive_windows_returns_selection(small_df):
    windows, selection = split_into_adaptive_windows(small_df)
    assert selection.selected_window_hours > 0
    assert selection.window_type == "adaptive"


def test_window_hours_clamped():
    cfg = AdaptiveWindowConfig(
        low_threshold=50, high_threshold=1000,
        long_window_hours=200,  # Will be clamped
        max_window_hours=72,
    )
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-15", periods=5, freq="1h", tz="UTC"),
        "cloud_user_id": ["U001"] * 5,
    })
    result = select_adaptive_window(df, cfg)
    assert result.selected_window_hours <= 72.0
