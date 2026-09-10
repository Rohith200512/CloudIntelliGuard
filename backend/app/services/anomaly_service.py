"""
Anomaly detection orchestration service — CloudIntelliGuard.

Orchestrates: graph feature extraction → PyG tensor building →
model inference → threshold application → explanation → DB write.

Supports both baseline and enhanced model types.
"""
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.database_models import (
    Anomaly, CloudEvent, GraphWindow, ModelRun,
)
from app.services.feature_engineering import (
    extract_raw_features, extract_derived_features, build_user_feature_vector,
)
from app.services.graph_builder import deserialize_graph, get_user_node_list
from app.ml.baseline.detector import BaselineAnomalyDetector, ThresholdConfig
from app.ml.explainability.explainer import explain_anomaly

TORCH_AVAILABLE = False
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    pass


async def run_inference(
    db: AsyncSession,
    graph_window_id: int,
    model_type: str,
    threshold: Optional[float] = None,
    threshold_type: str = "statistical",
    hyperparams: Optional[Dict[str, Any]] = None,
) -> List[Anomaly]:
    """
    Run anomaly detection on a graph window.

    Steps:
      1. Load the GraphWindow and its CloudEvents
      2. Build feature vectors for each user node
      3. Construct PyG tensors (or NumPy if PyTorch unavailable)
      4. Load/train model and detector
      5. Score each user
      6. Generate explanations
      7. Persist Anomaly records
      8. Return list of created Anomaly objects

    Returns:
        List of Anomaly ORM objects saved to the database.
    """
    # Load graph window
    gw_result = await db.execute(
        select(GraphWindow).where(GraphWindow.id == graph_window_id)
    )
    gw: Optional[GraphWindow] = gw_result.scalar_one_or_none()
    if gw is None:
        raise ValueError(f"GraphWindow {graph_window_id} not found.")

    if gw.graph_json is None:
        raise ValueError(f"GraphWindow {graph_window_id} has no graph data. Run preprocessing first.")

    # Load events for this window
    events_result = await db.execute(
        select(CloudEvent).where(
            CloudEvent.dataset_id == gw.dataset_id,
            CloudEvent.timestamp >= gw.start_time,
            CloudEvent.timestamp < gw.end_time,
        )
    )
    events = events_result.scalars().all()

    if not events:
        logger.warning(f"No events found for graph window {graph_window_id}.")
        return []

    # Build DataFrame
    from app.services.preprocessing import load_processed_dataframe
    df = load_processed_dataframe(events)

    if df.empty:
        return []

    # Get user nodes
    G = deserialize_graph(gw.graph_json)
    users = get_user_node_list(G)

    if not users:
        logger.warning(f"No user nodes in graph window {graph_window_id}.")
        return []

    # Build feature vectors per user
    feature_dim = 16
    user_features: List[List[float]] = []
    user_raw_list: List[Dict] = []
    user_derived_list: List[Dict] = []

    for uid in users:
        raw = extract_raw_features(df, uid)
        derived = extract_derived_features(
            df, uid,
            window_start=gw.start_time,
            window_end=gw.end_time,
        )
        vec = build_user_feature_vector(raw, derived, feature_dim)
        user_features.append(vec)
        user_raw_list.append(raw)
        user_derived_list.append(derived)

    features_np = np.array(user_features, dtype=np.float32)

    # Create model run record
    model_run = ModelRun(
        model_type=model_type,
        run_type="infer",
        dataset_id=gw.dataset_id,
        graph_window_id=graph_window_id,
        hyperparams=hyperparams or {},
        status="RUNNING",
    )
    db.add(model_run)
    await db.flush()

    t_infer_start = time.monotonic()

    try:
        anomaly_scores, is_anomaly_flags, threshold_used, embeddings = _run_model_inference(
            features_np=features_np,
            graph_json=gw.graph_json,
            model_type=model_type,
            threshold=threshold,
            threshold_type=threshold_type,
            hyperparams=hyperparams or {},
        )

        detection_latency_ms = (time.monotonic() - t_infer_start) * 1000

        # Persist anomaly records
        created_anomalies: List[Anomaly] = []
        for i, uid in enumerate(users):
            raw = user_raw_list[i]
            derived = user_derived_list[i]

            explanation = explain_anomaly(
                cloud_user_id=uid,
                anomaly_score=float(anomaly_scores[i]),
                is_anomaly=bool(is_anomaly_flags[i]),
                event_count=raw.get("event_count", 0),
                failed_request_count=derived.get("failed_count", 0) or 0,
                unique_services=derived.get("services", raw.get("services", [])),
                unusual_services=derived.get("first_time_services") or [],
                sensitive_resources=derived.get("sensitive_resources", []),
                new_resources=derived.get("first_time_resources") or [],
                historical_avg_requests=derived.get("historical_avg_daily_requests"),
                temporal_anomaly=False,
                is_coordinated=False,
            )

            anomaly = Anomaly(
                cloud_user_id=uid,
                graph_window_id=graph_window_id,
                model_run_id=model_run.id,
                anomaly_score=round(float(anomaly_scores[i]), 6),
                is_anomaly=bool(is_anomaly_flags[i]),
                threshold_used=threshold_used,
                threshold_type=threshold_type,
                embedding=embeddings[i] if embeddings else None,
                explanation=explanation.to_dict(),
            )
            db.add(anomaly)
            created_anomalies.append(anomaly)

        model_run.status = "COMPLETED"
        model_run.completed_at = datetime.now(timezone.utc)
        await db.commit()

        # Automatically compute risk scores and apply automated response enforcements
        from app.services.risk_service import compute_and_store_risk
        from app.services.incident_service import create_incident_from_anomaly

        for anom in created_anomalies:
            await db.refresh(anom)
            rs = await compute_and_store_risk(
                db=db,
                anomaly=anom,
                graph_window=gw,
                is_coordinated=False,
            )
            if anom.is_anomaly or rs.risk_level in ("HIGH", "CRITICAL"):
                try:
                    await create_incident_from_anomaly(
                        db=db,
                        anomaly=anom,
                        risk_score=rs,
                        graph_window=gw,
                    )
                except Exception as inc_err:
                    logger.warning(f"Could not auto-create incident: {inc_err}")

        logger.info(
            f"Inference complete: {len(created_anomalies)} users scored, "
            f"{sum(is_anomaly_flags)} anomalies, {detection_latency_ms:.1f}ms"
        )
        return created_anomalies

    except Exception as e:
        model_run.status = "FAILED"
        model_run.error_message = str(e)
        await db.commit()
        logger.error(f"Inference failed: {e}")
        raise


def _run_model_inference(
    features_np: np.ndarray,
    graph_json: Dict[str, Any],
    model_type: str,
    threshold: Optional[float],
    threshold_type: str,
    hyperparams: Dict[str, Any],
) -> tuple:
    """
    Execute model inference on feature vectors.

    Returns:
        (anomaly_scores, is_anomaly_flags, threshold_used, embeddings)
    """
    n_users = len(features_np)

    # Build edge_index from graph (user→action edges only, for simplicity)
    edge_index = _build_simple_edge_index(graph_json, features_np.shape[0])

    if TORCH_AVAILABLE:
        import torch
        x = torch.tensor(features_np, dtype=torch.float32)
        ei = torch.tensor(edge_index, dtype=torch.long)

        if model_type == "baseline":
            from app.ml.baseline.model import BaselineGCN
            from app.ml.baseline.trainer import train_baseline
            _, detector, _ = train_baseline(x, ei, hyperparams)
            # After training, re-run encode
            from app.ml.baseline.model import BaselineGCN
            gcn = BaselineGCN(
                in_channels=x.shape[1],
                hidden_channels=hyperparams.get("hidden_channels", settings.gnn_hidden_dim),
                out_channels=hyperparams.get("out_channels", settings.gnn_output_dim),
            )
            gcn_m = _wrap_gcn(gcn)
            gcn_m.eval()
            with torch.no_grad():
                emb, _ = gcn_m(x, ei)
            emb_np = emb.cpu().numpy()
            scores, flags = detector.predict(emb_np)
            threshold_used = detector.threshold_value or 0.5
            embeddings = emb_np.tolist()
        else:
            from app.ml.gnn.model import EnhancedTemporalGNN
            gnn = EnhancedTemporalGNN(
                in_channels=x.shape[1],
                hidden_channels=hyperparams.get("hidden_channels", settings.gnn_hidden_dim),
                out_channels=hyperparams.get("out_channels", settings.gnn_output_dim),
            )
            # For inference without training, use embedding distance-based scoring
            gnn_m = _wrap_enhanced(gnn)
            gnn_m.eval()
            with torch.no_grad():
                emb, _ = gnn_m(x, ei)
            emb_np = emb.cpu().numpy()
            detector = BaselineAnomalyDetector(
                threshold_config=ThresholdConfig(
                    method=threshold_type,
                    fixed_threshold=threshold,
                    contamination=hyperparams.get("contamination", 0.1),
                )
            )
            if len(emb_np) >= 2:
                detector.fit(emb_np)
                scores, flags = detector.predict(emb_np)
                threshold_used = detector.threshold_value or 0.5
            else:
                scores = np.zeros(n_users)
                flags = np.zeros(n_users, dtype=bool)
                threshold_used = threshold or 0.5
            embeddings = emb_np.tolist()
    else:
        # Fallback: distance-based scoring without PyTorch
        detector = BaselineAnomalyDetector(
            threshold_config=ThresholdConfig(
                method=threshold_type,
                fixed_threshold=threshold,
            )
        )
        if len(features_np) >= 2:
            detector.fit(features_np)
            scores, flags = detector.predict(features_np)
            threshold_used = detector.threshold_value or 0.5
        else:
            scores = np.zeros(n_users)
            flags = np.zeros(n_users, dtype=bool)
            threshold_used = threshold or 0.5
        embeddings = None

    return scores, flags.tolist(), threshold_used, embeddings


def _build_simple_edge_index(graph_json: Dict, n_nodes: int) -> list:
    """Build a simple self-loop edge index for isolated node processing."""
    # When no structural edges are available, use self-loops
    return [[i for i in range(n_nodes)], [i for i in range(n_nodes)]]


def _wrap_gcn(gcn):
    """Wrap BaselineGCN attributes into an nn.Module for inference."""
    try:
        import torch.nn as nn
        class _M(nn.Module):
            def __init__(self, g):
                super().__init__()
                self.convs = g.convs
                self.batch_norms = g.batch_norms
                self.reconstruction_head = g.reconstruction_head
                self._g = g
            def forward(self, x, ei):
                return self._g.forward(x, ei)
        return _M(gcn)
    except Exception:
        return gcn


def _wrap_enhanced(gnn):
    """Wrap EnhancedTemporalGNN into an nn.Module for inference."""
    try:
        import torch.nn as nn
        class _M(nn.Module):
            def __init__(self, g):
                super().__init__()
                self.convs = g.convs
                self.batch_norms = g.batch_norms
                self.reconstruction_head = g.reconstruction_head
                if hasattr(g, 'temporal_attention') and g.temporal_attention is not None:
                    self.temporal_attention = g.temporal_attention
                    self.temporal_norm = g.temporal_norm
                self._g = g
            def forward(self, x, ei):
                return self._g.forward(x, ei)
        return _M(gnn)
    except Exception:
        return gnn
