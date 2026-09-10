"""
Preprocessing service — CloudIntelliGuard.

Transforms raw CloudEvent records for a dataset into clean, analysis-ready data.

Steps:
  1. Load raw events from DB into a DataFrame
  2. Normalize timestamps to UTC
  3. Handle missing values per field rules
  4. Remove invalid records (null timestamp, null user_id)
  5. Normalize categorical fields (lowercase, strip whitespace)
  6. Deduplicate by event_id where available
  7. Sort events chronologically
  8. Write back to DB (update is_processed flag)
  9. Generate and return a preprocessing report
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.database_models import CloudEvent, Dataset


CATEGORICAL_COLUMNS = ["action", "service", "status", "cloud_user_id"]
SENSITIVE_SERVICES = {"iam", "secrets manager", "kms", "sts", "secretsmanager"}


async def preprocess_dataset(
    db: AsyncSession,
    dataset_id: int,
) -> Dict[str, Any]:
    """
    Preprocess all CloudEvent records for a dataset.

    Returns:
        preprocessing_report dict with record counts, drop reasons, field stats.
    """
    # Load raw events
    result = await db.execute(
        select(CloudEvent).where(CloudEvent.dataset_id == dataset_id)
    )
    events = result.scalars().all()

    if not events:
        return {
            "dataset_id": dataset_id,
            "status": "no_events",
            "raw_count": 0,
            "processed_count": 0,
            "dropped_count": 0,
        }

    raw_count = len(events)
    df = _events_to_dataframe(events)

    report: Dict[str, Any] = {
        "dataset_id": dataset_id,
        "raw_count": raw_count,
        "drop_reasons": {},
    }

    # Step 1: Normalize timestamps
    df, ts_dropped = _normalize_timestamps(df)
    if ts_dropped > 0:
        report["drop_reasons"]["invalid_timestamp"] = ts_dropped

    # Step 2: Drop records with no cloud_user_id
    before = len(df)
    df = df[df["cloud_user_id"].notna() & (df["cloud_user_id"] != "")]
    uid_dropped = before - len(df)
    if uid_dropped > 0:
        report["drop_reasons"]["missing_user_id"] = uid_dropped

    # Step 3: Normalize categorical fields
    df = _normalize_categoricals(df)

    # Step 4: Deduplicate by event_id (keep first occurrence)
    before = len(df)
    if "event_id" in df.columns:
        has_event_id = df["event_id"].notna() & (df["event_id"] != "")
        df_with_id = df[has_event_id].drop_duplicates(subset=["event_id"], keep="first")
        df_without_id = df[~has_event_id]
        df = pd.concat([df_with_id, df_without_id], ignore_index=True)
    dup_dropped = before - len(df)
    if dup_dropped > 0:
        report["drop_reasons"]["duplicate_event_id"] = dup_dropped

    # Step 5: Sort chronologically
    df = df.sort_values("timestamp").reset_index(drop=True)

    processed_count = len(df)
    dropped_count = raw_count - processed_count

    # Field fill rates
    fill_rates = {}
    for col in ["cloud_user_id", "action", "service", "resource", "source_ip", "status"]:
        if col in df.columns:
            fill_rates[col] = round(df[col].notna().mean(), 4)
    report["field_fill_rates"] = fill_rates

    # Time range
    if not df.empty:
        report["time_range_start"] = df["timestamp"].min().isoformat()
        report["time_range_end"] = df["timestamp"].max().isoformat()
        report["unique_users"] = int(df["cloud_user_id"].nunique())
        report["unique_services"] = int(df["service"].nunique()) if "service" in df.columns else 0
        report["unique_actions"] = int(df["action"].nunique()) if "action" in df.columns else 0

    report["processed_count"] = processed_count
    report["dropped_count"] = dropped_count
    report["status"] = "completed"

    # Update Dataset record
    dataset_result = await db.execute(
        select(Dataset).where(Dataset.id == dataset_id)
    )
    dataset = dataset_result.scalar_one_or_none()
    if dataset:
        dataset.status = "PROCESSED"
        dataset.processed_time = datetime.now(timezone.utc)
        dataset.processed_event_count = processed_count
        dataset.dropped_event_count = dropped_count
        dataset.preprocessing_report = report

    await db.commit()
    logger.info(
        f"Preprocessing complete for dataset {dataset_id}: "
        f"{processed_count} processed, {dropped_count} dropped."
    )
    return report


def _events_to_dataframe(events: List[CloudEvent]) -> pd.DataFrame:
    """Convert ORM CloudEvent objects to a pandas DataFrame."""
    rows = []
    for e in events:
        rows.append({
            "db_id": e.id,
            "event_id": e.event_id,
            "timestamp": e.timestamp,
            "cloud_user_id": e.cloud_user_id,
            "action": e.action,
            "service": e.service,
            "resource": e.resource,
            "source_ip": e.source_ip,
            "status": e.status,
        })
    return pd.DataFrame(rows)


def _normalize_timestamps(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """Convert all timestamps to UTC-aware datetime objects. Drop rows with invalid timestamps."""
    before = len(df)
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df[df["timestamp"].notna()]
    dropped = before - len(df)
    return df, dropped


def _normalize_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase and strip whitespace from categorical string columns."""
    df = df.copy()
    for col in CATEGORICAL_COLUMNS:
        if col in df.columns:
            df[col] = df[col].where(df[col].isna(), df[col].astype(str).str.strip().str.lower())
            df[col] = df[col].replace("nan", None)
    return df


def load_processed_dataframe(events: List[CloudEvent]) -> pd.DataFrame:
    """
    Convert a list of CloudEvent ORM objects to a clean analysis DataFrame.
    Used by downstream services (feature engineering, graph builder, etc.).
    """
    df = _events_to_dataframe(events)
    df, _ = _normalize_timestamps(df)
    df = _normalize_categoricals(df)
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df
