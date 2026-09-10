"""
Data ingestion service — CloudIntelliGuard.

Supports CloudTrail-style CSV and JSON files.
Validates required columns, handles missing values, and stores raw events.

Required columns (must be present):  timestamp, user_id (or cloud_user_id)
Optional columns (handled gracefully): event_id, action, service, resource,
                                        source_ip, status, api
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.database_models import Dataset, CloudEvent

# Columns that must be present in the uploaded file
REQUIRED_COLUMNS = {"timestamp"}

# Mapping of common column name aliases to our canonical names
COLUMN_ALIASES: Dict[str, str] = {
    "user_id": "cloud_user_id",
    "userId": "cloud_user_id",
    "userIdentity": "cloud_user_id",
    "userIdentityarn": "cloud_user_id",
    "userIdentityuserName": "cloud_user_id",
    "userIdentityprincipalId": "cloud_user_id",
    "api": "action",
    "eventName": "action",
    "apiAction": "action",
    "eventSource": "service",
    "sourceIPAddress": "source_ip",
    "errorCode": "status",
    "eventID": "event_id",
    "eventTime": "timestamp",
}

# Optional columns we know how to handle
KNOWN_OPTIONAL_COLUMNS = [
    "event_id", "cloud_user_id", "action", "service",
    "resource", "source_ip", "status",
]


class IngestionError(Exception):
    """Raised when an uploaded file cannot be ingested."""
    pass


def _load_raw_dataframe(file_path: str, file_type: str) -> pd.DataFrame:
    """Load a CSV or JSON file into a DataFrame."""
    if file_type == "csv":
        try:
            df = pd.read_csv(file_path, low_memory=False)
        except Exception as e:
            raise IngestionError(f"Failed to parse CSV: {e}")
    elif file_type == "json":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Support top-level list or {"Records": [...]} (CloudTrail format)
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                records = data.get("Records", data.get("events", data.get("items", None)))
                if records is None:
                    raise IngestionError("JSON file must contain a top-level list or a 'Records' key.")
                df = pd.DataFrame(records)
            else:
                raise IngestionError("Unsupported JSON structure.")
        except IngestionError:
            raise
        except Exception as e:
            raise IngestionError(f"Failed to parse JSON: {e}")
    else:
        raise IngestionError(f"Unsupported file type: {file_type}. Use csv or json.")

    return df


def _apply_column_aliases(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns using known aliases to canonical names."""
    rename_map = {col: COLUMN_ALIASES[col] for col in df.columns if col in COLUMN_ALIASES}
    return df.rename(columns=rename_map)


def _validate_required_columns(df: pd.DataFrame) -> None:
    """Raise IngestionError if any required column is missing."""
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise IngestionError(
            f"Missing required column(s): {missing}. "
            f"Present columns: {list(df.columns)}"
        )


def _save_raw_file(file_content: bytes, filename: str, dataset_id: int) -> str:
    """Save uploaded bytes to the raw data directory and return the path."""
    raw_dir = Path(settings.data_dir) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    dest = raw_dir / f"dataset_{dataset_id}_{filename}"
    dest.write_bytes(file_content)
    return str(dest)


async def ingest_file(
    db: AsyncSession,
    file_content: bytes,
    filename: str,
    uploaded_by: Optional[int] = None,
    is_demo: bool = False,
) -> Tuple[Dataset, Dict[str, Any]]:
    """
    Ingest a CloudTrail-style CSV or JSON file.

    Steps:
      1. Determine file type from extension
      2. Save raw file to disk
      3. Create Dataset record
      4. Load and validate DataFrame
      5. Apply column aliases
      6. Store raw events in DB
      7. Return Dataset and ingestion summary

    Returns:
        (Dataset ORM object, ingestion_summary dict)

    Raises:
        IngestionError on validation failures.
    """
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in ("csv", "json"):
        raise IngestionError(f"Unsupported file extension: {ext}. Only csv and json are accepted.")

    file_type = ext

    # Create Dataset record first (to get the ID for file naming)
    dataset = Dataset(
        filename=filename,
        file_path="pending",
        file_type=file_type,
        status="UPLOADED",
        uploaded_by=uploaded_by,
        is_demo=is_demo,
    )
    db.add(dataset)
    await db.flush()  # Get the ID without full commit

    # Save raw file
    file_path = _save_raw_file(file_content, filename, dataset.id)
    dataset.file_path = file_path

    # Load into DataFrame
    df = _load_raw_dataframe(file_path, file_type)
    raw_count = len(df)
    dataset.raw_event_count = raw_count

    # Apply aliases
    df = _apply_column_aliases(df)

    # Validate required columns
    _validate_required_columns(df)

    # Store raw events
    events_stored = 0
    for _, row in df.iterrows():
        raw_dict = row.where(row.notna(), other=None).to_dict()
        event = CloudEvent(
            dataset_id=dataset.id,
            event_id=str(raw_dict.get("event_id", "")) or None,
            timestamp=_parse_timestamp(raw_dict.get("timestamp")),
            cloud_user_id=str(raw_dict.get("cloud_user_id", "")) or None,
            action=str(raw_dict.get("action", "")) or None,
            service=str(raw_dict.get("service", "")) or None,
            resource=str(raw_dict.get("resource", "")) or None,
            source_ip=str(raw_dict.get("source_ip", "")) or None,
            status=str(raw_dict.get("status", "")) or None,
            raw_json=raw_dict,
        )
        # Skip rows where timestamp cannot be parsed
        if event.timestamp is None:
            continue
        db.add(event)
        events_stored += 1

    dataset.status = "UPLOADED"
    await db.commit()
    await db.refresh(dataset)

    summary = {
        "dataset_id": dataset.id,
        "filename": filename,
        "file_type": file_type,
        "raw_row_count": raw_count,
        "events_stored": events_stored,
        "columns_found": list(df.columns),
        "optional_columns_present": [c for c in KNOWN_OPTIONAL_COLUMNS if c in df.columns],
    }
    logger.info(f"Ingested dataset {dataset.id}: {events_stored}/{raw_count} events stored.")
    return dataset, summary


def _parse_timestamp(value: Any) -> Optional[datetime]:
    """Attempt to parse a timestamp value to a UTC-aware datetime."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        ts = pd.to_datetime(value, utc=True)
        return ts.to_pydatetime()
    except Exception:
        return None
