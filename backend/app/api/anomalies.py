"""Anomaly detection and model training/inference API routes."""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.logging import log_audit
from app.database.connection import get_db
from app.models.database_models import Anomaly, GraphWindow, ModelRun, User
from app.models.schemas import (
    AnomalyRead, MessageResponse, ModelInferRequest, ModelRunRead, ModelTrainRequest,
)
from app.services.anomaly_service import run_inference

router = APIRouter()


# ── Model management ──────────────────────────────────────────────────────────

@router.post("/models/train", response_model=ModelRunRead, status_code=status.HTTP_202_ACCEPTED,
             summary="Train anomaly detection model")
async def train_model(
    body: ModelTrainRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger model training on a dataset.

    Requires at least one processed GraphWindow for the dataset.
    Returns a ModelRun record; training is synchronous in Phase 1.
    """
    from app.services.preprocessing import load_processed_dataframe
    from app.services.feature_engineering import extract_raw_features, extract_derived_features, build_user_feature_vector
    from app.services.graph_builder import deserialize_graph, get_user_node_list
    from app.ml.baseline.trainer import train_baseline
    from app.ml.baseline.detector import ThresholdConfig
    import numpy as np

    # Find a graph window for this dataset
    gw_result = await db.execute(
        select(GraphWindow)
        .where(GraphWindow.dataset_id == body.dataset_id)
        .order_by(GraphWindow.created_at.desc())
        .limit(1)
    )
    gw = gw_result.scalar_one_or_none()
    if gw is None:
        raise HTTPException(status_code=404,
                            detail="No graph windows found. Run POST /datasets/{id}/process first.")

    model_run = ModelRun(
        model_type=body.model_type,
        run_type="train",
        dataset_id=body.dataset_id,
        graph_window_id=gw.id,
        hyperparams=body.hyperparams or {},
        status="RUNNING",
    )
    db.add(model_run)
    await db.commit()
    await db.flush()

    try:
        from app.models.database_models import CloudEvent
        events_result = await db.execute(
            select(CloudEvent).where(
                CloudEvent.dataset_id == body.dataset_id,
                CloudEvent.timestamp >= gw.start_time,
                CloudEvent.timestamp < gw.end_time,
            )
        )
        events = events_result.scalars().all()
        df = load_processed_dataframe(events)

        if df.empty or gw.graph_json is None:
            raise ValueError("No events or graph data for training window.")

        G = deserialize_graph(gw.graph_json)
        users = get_user_node_list(G)
        if not users:
            raise ValueError("No user nodes in graph.")

        feature_dim = 16
        features = []
        for uid in users:
            raw = extract_raw_features(df, uid)
            derived = extract_derived_features(df, uid, gw.start_time, gw.end_time)
            features.append(build_user_feature_vector(raw, derived, feature_dim))

        features_np = np.array(features, dtype=np.float32)

        # Self-loop edge index for isolated training
        n = len(users)
        edge_index_list = [[i for i in range(n)], [i for i in range(n)]]

        try:
            import torch
            x = torch.tensor(features_np)
            ei = torch.tensor(edge_index_list, dtype=torch.long)

            if body.model_type == "baseline":
                from app.ml.baseline.trainer import train_baseline
                from app.core.config import settings
                import os
                ckpt_path = os.path.join(
                    settings.checkpoint_dir,
                    f"baseline_dataset{body.dataset_id}.pt"
                )
                _, detector, metadata = train_baseline(x, ei, body.hyperparams, ckpt_path)
                model_run.model_checkpoint_path = ckpt_path
            else:
                from app.ml.gnn.model import EnhancedTemporalGNN
                from app.ml.baseline.detector import BaselineAnomalyDetector
                from app.core.config import settings
                gnn = EnhancedTemporalGNN(in_channels=feature_dim)
                # Basic training (same unsupervised approach as baseline)
                import torch.nn as nn
                from torch.optim import Adam

                class _M(nn.Module):
                    def __init__(self, g):
                        super().__init__()
                        self.convs = g.convs
                        self.batch_norms = g.batch_norms
                        self.reconstruction_head = g.reconstruction_head
                        self._g = g
                    def forward(self, xin, ei):
                        return self._g.forward(xin, ei)

                m = _M(gnn)
                opt = Adam(m.parameters(), lr=0.001)
                crit = nn.MSELoss()
                m.train()
                for ep in range(body.hyperparams.get("epochs", 100) if body.hyperparams else 100):
                    opt.zero_grad()
                    emb, rec = m(x, ei)
                    loss = crit(rec, x)
                    loss.backward()
                    opt.step()

                m.eval()
                with torch.no_grad():
                    emb, _ = m(x, ei)
                emb_np = emb.cpu().numpy()
                detector = BaselineAnomalyDetector()
                if len(emb_np) >= 2:
                    detector.fit(emb_np)

                import os
                ckpt_path = os.path.join(
                    settings.checkpoint_dir,
                    f"enhanced_dataset{body.dataset_id}.pt"
                )
                torch.save({"model_state": m.state_dict()}, ckpt_path)
                model_run.model_checkpoint_path = ckpt_path

        except ImportError:
            # PyTorch not available: use sklearn-only baseline
            from app.ml.baseline.detector import BaselineAnomalyDetector
            detector = BaselineAnomalyDetector()
            if len(features_np) >= 2:
                detector.fit(features_np)

        model_run.status = "COMPLETED"
        model_run.completed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(model_run)

        log_audit("model_trained", user_id=current_user.id,
                  resource=f"model_run/{model_run.id}",
                  detail={"model_type": body.model_type, "dataset_id": body.dataset_id})
        return model_run

    except Exception as e:
        model_run.status = "FAILED"
        model_run.error_message = str(e)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@router.post("/models/infer", response_model=List[AnomalyRead], status_code=status.HTTP_200_OK,
             summary="Run anomaly detection inference on a graph window")
async def infer(
    body: ModelInferRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run anomaly detection on a specific graph window."""
    try:
        anomalies = await run_inference(
            db=db,
            graph_window_id=body.graph_window_id,
            model_type=body.model_type,
            threshold=body.threshold,
            threshold_type=body.threshold_type,
        )
        log_audit("model_inference", user_id=current_user.id,
                  resource=f"graph_window/{body.graph_window_id}",
                  detail={"model_type": body.model_type, "anomalies": len(anomalies)})
        return anomalies
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")


# ── Anomaly queries ────────────────────────────────────────────────────────────

@router.get("/anomalies", response_model=List[AnomalyRead], summary="List anomalies")
async def list_anomalies(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
    cloud_user_id: Optional[str] = Query(None),
    graph_window_id: Optional[int] = Query(None),
    only_anomalies: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    q = select(Anomaly).order_by(Anomaly.created_at.desc())
    if cloud_user_id:
        q = q.where(Anomaly.cloud_user_id == cloud_user_id)
    if graph_window_id:
        q = q.where(Anomaly.graph_window_id == graph_window_id)
    if only_anomalies:
        q = q.where(Anomaly.is_anomaly == True)  # noqa
    q = q.offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/anomalies/{anomaly_id}", response_model=AnomalyRead, summary="Get anomaly by ID")
async def get_anomaly(
    anomaly_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Anomaly).where(Anomaly.id == anomaly_id))
    a = result.scalar_one_or_none()
    if a is None:
        raise HTTPException(status_code=404, detail="Anomaly not found.")
    return a
