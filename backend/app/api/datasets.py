"""Dataset upload and processing API routes."""
import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.config import settings
from app.core.logging import log_audit
from app.database.connection import get_db
from app.models.database_models import CloudEvent, Dataset, GraphWindow, User
from app.models.schemas import DatasetProcessRequest, DatasetRead, MessageResponse
from app.services.data_ingestion import IngestionError, ingest_file
from app.services.preprocessing import preprocess_dataset
from app.services.graph_builder import build_and_store_graph_window
from app.ml.temporal.adaptive import (
    AdaptiveWindowConfig, split_into_fixed_windows, split_into_adaptive_windows,
)

router = APIRouter()

@router.post("/upload", response_model=DatasetRead, status_code=status.HTTP_201_CREATED,
             summary="Upload a CloudTrail-style CSV or JSON dataset")
async def upload_dataset(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a CloudTrail-style CSV or JSON file for analysis.

    Required fields in the file: timestamp, user_id (or cloud_user_id)
    Optional fields: event_id, action, service, resource, source_ip, status
    """
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {settings.max_upload_size_mb} MB).",
        )

    try:
        dataset, summary = await ingest_file(
            db=db,
            file_content=content,
            filename=file.filename or "upload.csv",
            uploaded_by=current_user.id,
            is_demo=settings.demo_mode,
        )
    except IngestionError as e:
        raise HTTPException(status_code=422, detail=str(e))

    log_audit("dataset_uploaded", user_id=current_user.id,
              resource=f"dataset/{dataset.id}", detail=summary)
    return dataset


@router.get("", response_model=List[DatasetRead], summary="List all datasets")
async def list_datasets(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    result = await db.execute(
        select(Dataset).order_by(Dataset.upload_time.desc()).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.get("/{dataset_id}", response_model=DatasetRead, summary="Get dataset details")
async def get_dataset(
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return dataset


@router.post("/{dataset_id}/process", response_model=MessageResponse,
             summary="Preprocess dataset and build graph windows")
async def process_dataset(
    dataset_id: int,
    body: DatasetProcessRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Preprocess a dataset and construct temporal graph windows.

    - Normalizes timestamps, deduplicates, sorts events
    - Builds graph windows (fixed or adaptive)
    - Stores graph windows in the database
    """
    ds_result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = ds_result.scalar_one_or_none()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    if dataset.status == "PROCESSING":
        raise HTTPException(status_code=409, detail="Dataset is already being processed.")

    dataset.status = "PROCESSING"
    await db.commit()

    try:
        # Preprocess
        report = await preprocess_dataset(db, dataset_id)

        # Load processed events
        events_result = await db.execute(
            select(CloudEvent).where(CloudEvent.dataset_id == dataset_id)
        )
        events = events_result.scalars().all()

        from app.services.preprocessing import load_processed_dataframe
        df = load_processed_dataframe(events)

        if df.empty:
            return MessageResponse(
                message="Dataset processed but contains no valid events.",
                detail=report,
            )

        # Build graph windows
        window_type = body.window_type
        windows_created = 0

        if window_type == "adaptive":
            windows, selection = split_into_adaptive_windows(df)
            wh = selection.selected_window_hours
        else:
            wh = body.window_hours or float(settings.default_window_hours)
            windows = split_into_fixed_windows(df, wh)

        for window_df, w_start, w_end in windows:
            await build_and_store_graph_window(
                db=db,
                dataset_id=dataset_id,
                events_df=window_df,
                window_start=w_start,
                window_end=w_end,
                window_type=window_type,
                window_hours=wh,
            )
            windows_created += 1

        log_audit("dataset_processed", user_id=current_user.id,
                  resource=f"dataset/{dataset_id}",
                  detail={"windows_created": windows_created})

        return MessageResponse(
            message=f"Dataset processed. {windows_created} graph window(s) created.",
            detail={**report, "windows_created": windows_created, "window_type": window_type},
        )

    except Exception as e:
        ds_result2 = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
        ds = ds_result2.scalar_one_or_none()
        if ds:
            ds.status = "FAILED"
            await db.commit()
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
