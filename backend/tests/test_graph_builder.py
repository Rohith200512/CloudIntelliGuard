"""Unit tests for graph builder service."""
import pandas as pd
import pytest
from datetime import datetime, timezone

from app.services.graph_builder import (
    build_graph_from_dataframe,
    get_user_subgraph,
    serialize_graph,
    deserialize_graph,
    get_user_node_list,
)


@pytest.fixture
def events_df():
    return pd.DataFrame([
        {"cloud_user_id": "u001", "action": "listbuckets", "service": "s3",
         "resource": "arn:aws:s3:::bucket", "status": "success",
         "timestamp": pd.Timestamp("2024-01-15T08:00:00Z")},
        {"cloud_user_id": "u001", "action": "getobject", "service": "s3",
         "resource": "arn:aws:s3:::bucket/file.txt", "status": "success",
         "timestamp": pd.Timestamp("2024-01-15T09:00:00Z")},
        {"cloud_user_id": "u002", "action": "getuser", "service": "iam",
         "resource": "arn:aws:iam::123:user/admin", "status": "failure",
         "timestamp": pd.Timestamp("2024-01-15T02:00:00Z")},
    ])


def test_build_graph_creates_user_nodes(events_df):
    G = build_graph_from_dataframe(events_df)
    user_nodes = [n for n in G.nodes if "user::" in n]
    assert len(user_nodes) == 2


def test_build_graph_creates_edges(events_df):
    G = build_graph_from_dataframe(events_df)
    assert G.number_of_edges() > 0


def test_build_graph_node_types(events_df):
    G = build_graph_from_dataframe(events_df)
    node_types = {G.nodes[n]["node_type"] for n in G.nodes}
    assert "user" in node_types
    assert "action" in node_types
    assert "service" in node_types
    assert "resource" in node_types


def test_empty_dataframe():
    G = build_graph_from_dataframe(pd.DataFrame())
    assert G.number_of_nodes() == 0


def test_get_user_subgraph(events_df):
    G = build_graph_from_dataframe(events_df)
    sg = get_user_subgraph(G, "u001")
    assert sg.number_of_nodes() > 0


def test_get_user_subgraph_missing_user(events_df):
    G = build_graph_from_dataframe(events_df)
    sg = get_user_subgraph(G, "NONEXISTENT")
    assert sg.number_of_nodes() == 0


def test_serialize_deserialize_roundtrip(events_df):
    G = build_graph_from_dataframe(events_df)
    data = serialize_graph(G)
    G2 = deserialize_graph(data)
    assert G2.number_of_nodes() == G.number_of_nodes()
    assert G2.number_of_edges() == G.number_of_edges()


def test_get_user_node_list(events_df):
    G = build_graph_from_dataframe(events_df)
    users = get_user_node_list(G)
    assert "u001" in users
    assert "u002" in users
