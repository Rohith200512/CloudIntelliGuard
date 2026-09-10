"""
Dynamic temporal graph construction service — CloudIntelliGuard.

Builds a NetworkX directed multigraph from a window of cloud events.

Node types:
  - user     : Cloud IAM user (cloud_user_id)
  - action   : API action (action)
  - service  : Cloud service (service)
  - resource : Cloud resource (resource)

Edge types:
  - user → action       (user_performed_action)
  - action → service    (action_targets_service)
  - service → resource  (service_on_resource)

Each edge carries temporal and contextual attributes.
Graph is serialized to NetworkX node-link JSON format for storage and reuse.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import logger
from app.models.database_models import CloudEvent, Dataset, GraphWindow


# Node type prefix constants
NODE_USER = "user"
NODE_IP = "ip"
NODE_ACTION = "action"
NODE_SERVICE = "service"
NODE_RESOURCE = "resource"


def _make_node_id(node_type: str, value: str) -> str:
    """Create a prefixed node identifier."""
    return f"{node_type}::{value}"


def build_graph_from_dataframe(
    events_df: pd.DataFrame,
    window_start: Optional[datetime] = None,
    window_end: Optional[datetime] = None,
) -> nx.DiGraph:
    """
    Build a directed temporal graph from a window DataFrame.

    Entities:
      User → IP → Action → Service → Resource

    Edge attributes:
      - timestamp    : event timestamp (ISO string)
      - status       : Success | Failure | None
      - weight       : frequency-weighted
      - edge_type    : edge relationship label
    """
    G = nx.DiGraph()

    # Graph-level metadata
    G.graph["window_start"] = window_start.isoformat() if window_start else None
    G.graph["window_end"] = window_end.isoformat() if window_end else None
    G.graph["event_count"] = len(events_df)

    for _, row in events_df.iterrows():
        ts = row.get("timestamp")
        ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts) if ts else None
        status = str(row.get("status", "")) or None
        user_val = str(row.get("cloud_user_id", "")).strip()
        ip_val = str(row.get("source_ip", "")).strip()
        action_val = str(row.get("action", "")).strip()
        service_val = str(row.get("service", "")).strip()
        resource_val = str(row.get("resource", "")).strip()

        if not user_val or user_val == "nan":
            continue

        user_node = _make_node_id(NODE_USER, user_val)
        _add_node(G, user_node, NODE_USER, user_val)

        # IP node & edge (if valid)
        if ip_val and ip_val != "nan":
            ip_node = _make_node_id(NODE_IP, ip_val)
            _add_node(G, ip_node, NODE_IP, ip_val)
            _add_or_update_edge(
                G, user_node, ip_node,
                edge_type="user_originates_from_ip",
                timestamp=ts_str,
                status=status,
            )

        if action_val and action_val != "nan":
            action_node = _make_node_id(NODE_ACTION, action_val)
            _add_node(G, action_node, NODE_ACTION, action_val)
            
            # Direct user -> action edge
            _add_or_update_edge(
                G, user_node, action_node,
                edge_type="user_performed_action",
                timestamp=ts_str,
                status=status,
            )
            
            # If IP exists, also connect IP -> action for attack path tracing
            if ip_val and ip_val != "nan":
                _add_or_update_edge(
                    G, ip_node, action_node,
                    edge_type="ip_initiates_action",
                    timestamp=ts_str,
                    status=status,
                )

            if service_val and service_val != "nan":
                service_node = _make_node_id(NODE_SERVICE, service_val)
                _add_node(G, service_node, NODE_SERVICE, service_val)
                _add_or_update_edge(
                    G, action_node, service_node,
                    edge_type="action_targets_service",
                    timestamp=ts_str,
                    status=status,
                )

                if resource_val and resource_val != "nan":
                    resource_node = _make_node_id(NODE_RESOURCE, resource_val)
                    _add_node(G, resource_node, NODE_RESOURCE, resource_val)
                    _add_or_update_edge(
                        G, service_node, resource_node,
                        edge_type="service_on_resource",
                        timestamp=ts_str,
                        status=status,
                    )

    return G


def _add_node(G: nx.DiGraph, node_id: str, node_type: str, label: str) -> None:
    """Add a node if not already present."""
    if node_id not in G:
        G.add_node(node_id, node_type=node_type, label=label, weight=0)
    G.nodes[node_id]["weight"] = G.nodes[node_id].get("weight", 0) + 1


def _add_or_update_edge(
    G: nx.DiGraph,
    src: str,
    dst: str,
    edge_type: str,
    timestamp: Optional[str],
    status: Optional[str],
) -> None:
    """Add an edge or increment its weight if it already exists."""
    if G.has_edge(src, dst):
        G[src][dst]["weight"] = G[src][dst].get("weight", 1) + 1
        # Keep the most recent timestamp
        existing_ts = G[src][dst].get("last_timestamp")
        if timestamp and (not existing_ts or timestamp > existing_ts):
            G[src][dst]["last_timestamp"] = timestamp
        # Track failure count
        if status and "fail" in status.lower():
            G[src][dst]["failure_count"] = G[src][dst].get("failure_count", 0) + 1
    else:
        G.add_edge(
            src, dst,
            edge_type=edge_type,
            first_timestamp=timestamp,
            last_timestamp=timestamp,
            weight=1,
            failure_count=1 if (status and "fail" in status.lower()) else 0,
        )


def get_user_subgraph(G: nx.DiGraph, cloud_user_id: str) -> nx.DiGraph:
    """Extract the ego subgraph centred on a specific user node."""
    user_node = _make_node_id(NODE_USER, cloud_user_id)
    if user_node not in G:
        return nx.DiGraph()
    # 2-hop neighbourhood
    nodes = nx.single_source_shortest_path_length(G, user_node, cutoff=2)
    return G.subgraph(list(nodes.keys())).copy()


def serialize_graph(G: nx.DiGraph) -> Dict[str, Any]:
    """Serialize a NetworkX graph to a JSON-serializable dict (node-link format)."""
    return nx.node_link_data(G)


def deserialize_graph(data: Dict[str, Any]) -> nx.DiGraph:
    """Deserialize a node-link dict back to a NetworkX DiGraph."""
    return nx.node_link_graph(data, directed=True)


def get_user_node_list(G: nx.DiGraph) -> List[str]:
    """Return a list of cloud_user_id values present in the graph."""
    return [
        G.nodes[n]["label"]
        for n in G.nodes
        if G.nodes[n].get("node_type") == NODE_USER
    ]


async def build_and_store_graph_window(
    db: AsyncSession,
    dataset_id: int,
    events_df: pd.DataFrame,
    window_start: datetime,
    window_end: datetime,
    window_type: str,
    window_hours: Optional[float] = None,
) -> GraphWindow:
    """
    Build a graph from a window DataFrame and persist it as a GraphWindow record.

    Returns the created GraphWindow ORM object.
    """
    t_start = time.monotonic()

    G = build_graph_from_dataframe(events_df, window_start, window_end)
    graph_json = serialize_graph(G)

    elapsed_ms = (time.monotonic() - t_start) * 1000

    gw = GraphWindow(
        dataset_id=dataset_id,
        window_type=window_type,
        window_hours=window_hours,
        start_time=window_start,
        end_time=window_end,
        event_count=len(events_df),
        node_count=G.number_of_nodes(),
        edge_count=G.number_of_edges(),
        graph_json=graph_json,
        processing_time_ms=round(elapsed_ms, 2),
    )
    db.add(gw)
    await db.commit()
    await db.refresh(gw)

    logger.info(
        f"Built graph window {gw.id}: "
        f"{G.number_of_nodes()} nodes, {G.number_of_edges()} edges, "
        f"{len(events_df)} events, {elapsed_ms:.1f}ms"
    )
    return gw
