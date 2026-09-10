"""
Adaptive Time Window Strategy — CloudIntelliGuard.

DOCUMENTED HEURISTIC STRATEGY (not claimed to be optimal):
  Low activity  (events < low_threshold)  → longer window (captures more context)
  High activity (events > high_threshold) → shorter window (finer granularity)
  Medium activity                         → default window

Parameters are fully configurable. This strategy is a transparent starting
point intended to be experimentally improved in future iterations.
"""
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import pandas as pd

from app.core.config import settings
from app.core.logging import logger


@dataclass
class AdaptiveWindowConfig:
    """Configurable parameters for adaptive window selection."""
    low_threshold: int = 0
    high_threshold: int = 0
    long_window_hours: float = 48.0
    default_window_hours: float = 24.0
    short_window_hours: float = 6.0
    min_window_hours: float = 1.0
    max_window_hours: float = 72.0

    def __post_init__(self) -> None:
        if self.low_threshold == 0:
            self.low_threshold = settings.adaptive_low_threshold
        if self.high_threshold == 0:
            self.high_threshold = settings.adaptive_high_threshold


@dataclass
class WindowSelectionRecord:
    """Auditable record of an adaptive window selection decision."""
    selected_window_hours: float
    window_type: str
    event_count: int
    selection_rationale: str
    processing_time_ms: float


def select_adaptive_window(
    events_df: pd.DataFrame,
    config: Optional[AdaptiveWindowConfig] = None,
) -> WindowSelectionRecord:
    """
    Select an analysis window size based on event volume.

    Strategy (heuristic, configurable):
      - Count total events in the DataFrame
      - Compare against configured thresholds
      - Select window duration accordingly
      - Clamp to [min_window_hours, max_window_hours]

    Returns a WindowSelectionRecord with the decision and its rationale.
    """
    t0 = time.monotonic()
    config = config or AdaptiveWindowConfig()

    if events_df.empty:
        return WindowSelectionRecord(
            selected_window_hours=config.default_window_hours,
            window_type="adaptive",
            event_count=0,
            selection_rationale="No events; defaulting to standard window.",
            processing_time_ms=0.0,
        )

    n = len(events_df)

    if n < config.low_threshold:
        selected = config.long_window_hours
        rationale = (
            f"LOW activity ({n} events < threshold {config.low_threshold}). "
            f"Using longer window ({selected}h) to capture broader context."
        )
    elif n > config.high_threshold:
        selected = config.short_window_hours
        rationale = (
            f"HIGH activity ({n} events > threshold {config.high_threshold}). "
            f"Using shorter window ({selected}h) for finer granularity."
        )
    else:
        selected = config.default_window_hours
        rationale = (
            f"MEDIUM activity ({n} events between thresholds). "
            f"Using default window ({selected}h)."
        )

    selected = max(config.min_window_hours, min(config.max_window_hours, selected))
    elapsed = (time.monotonic() - t0) * 1000

    logger.info(f"Adaptive window: {selected}h selected — {rationale}")
    return WindowSelectionRecord(
        selected_window_hours=selected,
        window_type="adaptive",
        event_count=n,
        selection_rationale=rationale,
        processing_time_ms=round(elapsed, 3),
    )


def split_into_fixed_windows(
    events_df: pd.DataFrame,
    window_hours: float,
    timestamp_col: str = "timestamp",
) -> List[Tuple[pd.DataFrame, datetime, datetime]]:
    """
    Split a DataFrame into fixed-size time windows.

    Returns:
        List of (window_df, start_time, end_time) tuples (only non-empty windows).
    """
    if events_df.empty:
        return []

    df = events_df.copy()
    df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True)

    min_ts = df[timestamp_col].min()
    max_ts = df[timestamp_col].max()
    delta = timedelta(hours=window_hours)

    # Align to hour boundary
    start = min_ts.replace(minute=0, second=0, microsecond=0)
    windows: List[Tuple[pd.DataFrame, datetime, datetime]] = []

    while start <= max_ts:
        end = start + delta
        mask = (df[timestamp_col] >= start) & (df[timestamp_col] < end)
        window_df = df[mask]
        if not window_df.empty:
            windows.append((window_df.copy(), start.to_pydatetime(), end.to_pydatetime()))
        start = end

    return windows


def split_into_adaptive_windows(
    events_df: pd.DataFrame,
    config: Optional[AdaptiveWindowConfig] = None,
    timestamp_col: str = "timestamp",
) -> Tuple[List[Tuple[pd.DataFrame, datetime, datetime]], WindowSelectionRecord]:
    """
    Select an adaptive window size and split events accordingly.

    Returns:
        (list_of_windows, WindowSelectionRecord)
    """
    selection = select_adaptive_window(events_df, config)
    windows = split_into_fixed_windows(events_df, selection.selected_window_hours, timestamp_col)
    return windows, selection
