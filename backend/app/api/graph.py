"""Graph inspection API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database.connection import get_db
from app.models.database_models import GraphWindow, User
from app.models.schemas import GraphWindowRead, GraphWindowWithData
from app.services.graph_builder import deserialize_graph, get_user_subgraph, serialize_graph

router = APIRouter()


@router.get("/{window_id}", response_model=GraphWindowWithData,
            summary="Get graph window with full graph data")
async def get_graph_window(
    window_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
    include_graph: bool = True,
):
    result = await db.execute(select(GraphWindow).where(GraphWindow.id == window_id))
    gw = result.scalar_one_or_none()
    if gw is None:
        raise HTTPException(status_code=404, detail="GraphWindow not found.")
    if not include_graph:
        gw.graph_json = None
    return gw


@router.get("/user/{cloud_user_id}", summary="Get user ego subgraph from latest window")
async def get_user_subgraph_api(
    cloud_user_id: str,
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return the 2-hop ego subgraph centred on a cloud user from the most recent window."""
    result = await db.execute(
        select(GraphWindow)
        .where(GraphWindow.dataset_id == dataset_id)
        .order_by(GraphWindow.created_at.desc())
        .limit(1)
    )
    gw = result.scalar_one_or_none()
    if gw is None or gw.graph_json is None:
        raise HTTPException(status_code=404, detail="No graph data found for this dataset.")

    G = deserialize_graph(gw.graph_json)
    subgraph = get_user_subgraph(G, cloud_user_id)
    return {
        "cloud_user_id": cloud_user_id,
        "window_id": gw.id,
        "node_count": subgraph.number_of_nodes(),
        "edge_count": subgraph.number_of_edges(),
        "graph": serialize_graph(subgraph),
    }
