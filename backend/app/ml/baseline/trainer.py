"""
Baseline GCN trainer — unsupervised reconstruction loss.
"""
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

from app.core.config import settings
from app.core.logging import logger
from app.ml.baseline.detector import BaselineAnomalyDetector, ThresholdConfig

TORCH_AVAILABLE = False
try:
    import torch
    import torch.nn as nn
    from torch.optim import Adam
    TORCH_AVAILABLE = True
except ImportError:
    pass


def train_baseline(
    node_features: Any,
    edge_index: Any,
    hyperparams: Optional[Dict[str, Any]] = None,
    checkpoint_path: Optional[str] = None,
) -> Tuple[Any, BaselineAnomalyDetector, Dict[str, Any]]:
    """
    Train the baseline GCN and fit the anomaly detector.

    Args:
        node_features: torch.Tensor (num_nodes, num_features)
        edge_index:    torch.Tensor (2, num_edges)
        hyperparams:   optional dict to override defaults
        checkpoint_path: path to save model checkpoint

    Returns:
        (trained_model, fitted_detector, metadata_dict)
    """
    if not TORCH_AVAILABLE:
        raise ImportError("PyTorch is required for baseline training.")

    from app.ml.baseline.model import BaselineGCN

    hp: Dict[str, Any] = {
        "hidden_channels": settings.gnn_hidden_dim,
        "out_channels": settings.gnn_output_dim,
        "num_layers": settings.gnn_num_layers,
        "dropout": settings.gnn_dropout,
        "lr": 0.001,
        "epochs": 100,
        "weight_decay": 1e-5,
        "threshold_method": "statistical",
        "threshold_n_sigma": 2.0,
        "contamination": 0.1,
    }
    if hyperparams:
        hp.update(hyperparams)

    in_channels = node_features.shape[1]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    gcn = BaselineGCN(
        in_channels=in_channels,
        hidden_channels=hp["hidden_channels"],
        out_channels=hp["out_channels"],
        num_layers=hp["num_layers"],
        dropout=hp["dropout"],
    )

    # Convert BaselineGCN to nn.Module for training
    class _Module(nn.Module):
        def __init__(self, gcn_obj):
            super().__init__()
            self.convs = gcn_obj.convs
            self.batch_norms = gcn_obj.batch_norms
            self.reconstruction_head = gcn_obj.reconstruction_head
            self._gcn = gcn_obj

        def forward(self, x, edge_index):
            return self._gcn.forward(x, edge_index)

    module = _Module(gcn).to(device)
    x = node_features.to(device)
    ei = edge_index.to(device)

    optimizer = Adam(module.parameters(), lr=hp["lr"], weight_decay=hp["weight_decay"])
    criterion = nn.MSELoss()

    logger.info(f"Baseline training: {hp['epochs']} epochs on {device}")
    t0 = time.monotonic()
    losses = []

    module.train()
    for epoch in range(hp["epochs"]):
        optimizer.zero_grad()
        emb, rec = module(x, ei)
        loss = criterion(rec, x)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.item()))
        if (epoch + 1) % 20 == 0:
            logger.info(f"Epoch {epoch+1}/{hp['epochs']} loss={loss.item():.6f}")

    runtime_s = time.monotonic() - t0

    module.eval()
    with torch.no_grad():
        embeddings, _ = module(x, ei)
        emb_np = embeddings.cpu().numpy()

    # Fit anomaly detector on training embeddings
    detector = BaselineAnomalyDetector(
        threshold_config=ThresholdConfig(
            method=hp["threshold_method"],
            statistical_n_sigma=hp["threshold_n_sigma"],
            contamination=hp["contamination"],
        )
    )
    detector.fit(emb_np)

    if checkpoint_path:
        Path(checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            "model_state_dict": module.state_dict(),
            "model_config": gcn.get_config(),
            "hyperparams": hp,
            "final_loss": losses[-1],
        }, checkpoint_path)
        logger.info(f"Baseline checkpoint saved: {checkpoint_path}")

    metadata = {
        "model_type": "baseline",
        "hyperparams": hp,
        "training_time_s": runtime_s,
        "final_loss": losses[-1],
        "threshold_info": detector.get_threshold_info(),
        "device": str(device),
    }
    logger.info(f"Baseline training done. Loss={losses[-1]:.6f}, Time={runtime_s:.1f}s")
    return module, detector, metadata
