"""
Baseline GNN model — CloudIntelliGuard.

A static single-snapshot GCN used as the comparison baseline.
This is NOT claimed to be an exact reproduction of any published paper.
It is a standard GCN applied to a static cloud activity graph snapshot.
"""
from typing import Any, Dict, Optional, Tuple

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch import Tensor
    from torch_geometric.nn import GCNConv
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class BaselineGCN:
    """
    Baseline 2-layer GCN for node embedding generation.

    Produces per-node embeddings from a static graph snapshot.
    An unsupervised reconstruction loss is used for training.

    All hyperparameters are configurable via get_config / constructor.
    """

    def __init__(
        self,
        in_channels: int,
        hidden_channels: int = 64,
        out_channels: int = 32,
        num_layers: int = 2,
        dropout: float = 0.3,
    ):
        if not TORCH_AVAILABLE:
            raise ImportError(
                "PyTorch and torch_geometric are required. "
                "Install: pip install torch torch-geometric"
            )
        import torch.nn as nn
        from torch_geometric.nn import GCNConv

        self.in_channels = in_channels
        self.hidden_channels = hidden_channels
        self.out_channels = out_channels
        self.num_layers = max(num_layers, 2)
        self.dropout = dropout

        self._build_model()

    def _build_model(self) -> None:
        import torch.nn as nn
        from torch_geometric.nn import GCNConv

        convs = []
        bns = []

        convs.append(GCNConv(self.in_channels, self.hidden_channels))
        bns.append(nn.BatchNorm1d(self.hidden_channels))

        for _ in range(self.num_layers - 2):
            convs.append(GCNConv(self.hidden_channels, self.hidden_channels))
            bns.append(nn.BatchNorm1d(self.hidden_channels))

        convs.append(GCNConv(self.hidden_channels, self.out_channels))
        bns.append(nn.BatchNorm1d(self.out_channels))

        self.convs = nn.ModuleList(convs)
        self.batch_norms = nn.ModuleList(bns)

        self.reconstruction_head = nn.Sequential(
            nn.Linear(self.out_channels, self.hidden_channels),
            nn.ReLU(),
            nn.Linear(self.hidden_channels, self.in_channels),
        )

    def encode(self, x: "Tensor", edge_index: "Tensor") -> "Tensor":
        """Produce node embeddings."""
        import torch.nn.functional as F
        for i, (conv, bn) in enumerate(zip(self.convs, self.batch_norms)):
            x = conv(x, edge_index)
            x = bn(x)
            if i < len(self.convs) - 1:
                x = F.relu(x)
                x = F.dropout(x, p=self.dropout, training=False)
        return x

    def reconstruct(self, embedding: "Tensor") -> "Tensor":
        return self.reconstruction_head(embedding)

    def forward(self, x: "Tensor", edge_index: "Tensor") -> "Tuple[Tensor, Tensor]":
        emb = self.encode(x, edge_index)
        rec = self.reconstruct(emb)
        return emb, rec

    def get_config(self) -> Dict[str, Any]:
        return {
            "model_type": "BaselineGCN",
            "in_channels": self.in_channels,
            "hidden_channels": self.hidden_channels,
            "out_channels": self.out_channels,
            "num_layers": self.num_layers,
            "dropout": self.dropout,
        }
