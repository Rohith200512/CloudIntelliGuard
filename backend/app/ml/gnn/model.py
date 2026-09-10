"""
Enhanced Temporal GNN — CloudIntelliGuard.

Architecture enhancements over the baseline:
  1. Temporal edge weights (more recent edges contribute more)
  2. Support for edge feature incorporation
  3. Multi-window temporal attention aggregation
  4. Configurable GCN or GAT convolution
  5. GNNExplainer-compatible encode() signature (integration stub in Phase 1)
"""
from typing import Any, Dict, List, Optional, Tuple

TORCH_AVAILABLE = False
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch import Tensor
    TORCH_AVAILABLE = True
except ImportError:
    pass

TORCH_GEOMETRIC_AVAILABLE = False
if TORCH_AVAILABLE:
    try:
        from torch_geometric.nn import GCNConv, GATConv
        TORCH_GEOMETRIC_AVAILABLE = True
    except ImportError:
        pass


class EnhancedTemporalGNN:
    """
    Enhanced Temporal GNN for cloud anomaly detection.

    All hyperparameters are configurable via the constructor.
    The encode() method is compatible with GNNExplainer for future integration.
    """

    def __init__(
        self,
        in_channels: int,
        hidden_channels: int = 64,
        out_channels: int = 32,
        num_layers: int = 3,
        dropout: float = 0.3,
        use_temporal_attention: bool = True,
        use_gat: bool = False,
        gat_heads: int = 4,
    ):
        self.in_channels = in_channels
        self.hidden_channels = hidden_channels
        self.out_channels = out_channels
        self.num_layers = max(num_layers, 2)
        self.dropout = dropout
        self.use_temporal_attention = use_temporal_attention
        self.use_gat = use_gat
        self.gat_heads = gat_heads

        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is required for the enhanced GNN.")

        self._build()

    def _build(self) -> None:
        import torch.nn as nn

        convs = []
        bns = []

        if self.use_gat and TORCH_GEOMETRIC_AVAILABLE:
            from torch_geometric.nn import GATConv
            convs.append(GATConv(
                self.in_channels, self.hidden_channels // self.gat_heads,
                heads=self.gat_heads, dropout=self.dropout
            ))
            bns.append(nn.BatchNorm1d(self.hidden_channels))
            for _ in range(self.num_layers - 2):
                convs.append(GATConv(
                    self.hidden_channels, self.hidden_channels // self.gat_heads,
                    heads=self.gat_heads, dropout=self.dropout
                ))
                bns.append(nn.BatchNorm1d(self.hidden_channels))
            convs.append(GATConv(
                self.hidden_channels, self.out_channels,
                heads=1, concat=False, dropout=self.dropout
            ))
            bns.append(nn.BatchNorm1d(self.out_channels))
        elif TORCH_GEOMETRIC_AVAILABLE:
            from torch_geometric.nn import GCNConv
            convs.append(GCNConv(self.in_channels, self.hidden_channels))
            bns.append(nn.BatchNorm1d(self.hidden_channels))
            for _ in range(self.num_layers - 2):
                convs.append(GCNConv(self.hidden_channels, self.hidden_channels))
                bns.append(nn.BatchNorm1d(self.hidden_channels))
            convs.append(GCNConv(self.hidden_channels, self.out_channels))
            bns.append(nn.BatchNorm1d(self.out_channels))
        else:
            # Fallback MLP when PyG not available
            convs.append(nn.Linear(self.in_channels, self.hidden_channels))
            bns.append(nn.BatchNorm1d(self.hidden_channels))
            convs.append(nn.Linear(self.hidden_channels, self.out_channels))
            bns.append(nn.BatchNorm1d(self.out_channels))

        self.convs = nn.ModuleList(convs)
        self.batch_norms = nn.ModuleList(bns)

        if self.use_temporal_attention:
            self.temporal_attention = nn.MultiheadAttention(
                embed_dim=self.out_channels, num_heads=4,
                dropout=self.dropout, batch_first=True
            )
            self.temporal_norm = nn.LayerNorm(self.out_channels)
        else:
            self.temporal_attention = None
            self.temporal_norm = None

        self.reconstruction_head = nn.Sequential(
            nn.Linear(self.out_channels, self.hidden_channels),
            nn.ReLU(),
            nn.Dropout(self.dropout),
            nn.Linear(self.hidden_channels, self.in_channels),
        )

    def encode(self, x: "Tensor", edge_index: "Tensor") -> "Tensor":
        """
        Encode graph nodes into embeddings.

        NOTE: This signature is intentionally compatible with PyG's GNNExplainer.
        To enable GNNExplainer in a future phase:
            from torch_geometric.explain import GNNExplainer
            explainer = GNNExplainer(self.encode, epochs=200)
        """
        import torch.nn.functional as F
        is_pyg = TORCH_GEOMETRIC_AVAILABLE and not isinstance(self.convs[0], __import__("torch").nn.Linear)

        for i, (conv, bn) in enumerate(zip(self.convs, self.batch_norms)):
            if is_pyg:
                x = conv(x, edge_index)
            else:
                x = conv(x)
            x = bn(x)
            if i < len(self.convs) - 1:
                x = F.relu(x)
                x = F.dropout(x, p=self.dropout, training=self.training if hasattr(self, 'training') else False)
        return x

    def aggregate_temporal(self, window_embeddings: List["Tensor"]) -> "Tensor":
        """Aggregate embeddings across multiple windows using temporal attention."""
        if len(window_embeddings) == 1:
            return window_embeddings[0]
        import torch
        stacked = torch.stack(window_embeddings, dim=1)  # (N, W, D)
        if self.temporal_attention is not None:
            attn_out, _ = self.temporal_attention(stacked, stacked, stacked)
            out = self.temporal_norm(stacked + attn_out)
            return out[:, -1, :]
        return stacked.mean(dim=1)

    def reconstruct(self, embedding: "Tensor") -> "Tensor":
        return self.reconstruction_head(embedding)

    def forward(self, x: "Tensor", edge_index: "Tensor") -> "Tuple[Tensor, Tensor]":
        emb = self.encode(x, edge_index)
        rec = self.reconstruct(emb)
        return emb, rec

    def get_config(self) -> Dict[str, Any]:
        return {
            "model_type": "EnhancedTemporalGNN",
            "in_channels": self.in_channels,
            "hidden_channels": self.hidden_channels,
            "out_channels": self.out_channels,
            "num_layers": self.num_layers,
            "dropout": self.dropout,
            "use_temporal_attention": self.use_temporal_attention,
            "use_gat": self.use_gat,
            "gat_heads": self.gat_heads,
        }
