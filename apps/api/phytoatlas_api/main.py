"""FastAPI application for PhytoAtlas."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .graph_store import DEFAULT_GRAPH_DB, GraphStoreError, SQLiteGraphStore


def get_graph_store() -> SQLiteGraphStore:
    return SQLiteGraphStore(Path(os.getenv("PHYTOATLAS_GRAPH_DB", DEFAULT_GRAPH_DB)))


app = FastAPI(title="PhytoAtlas API", version="0.1.0")

origins = [
    origin.strip()
    for origin in os.getenv(
        "PHYTOATLAS_CORS_ORIGINS",
        "http://localhost:4322,http://127.0.0.1:4322,http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/graph/summary")
def graph_summary() -> dict:
    try:
        return get_graph_store().get_summary()
    except GraphStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/graph/nodes/{node_id:path}")
def graph_node(node_id: str) -> dict:
    try:
        node = get_graph_store().get_node(node_id)
    except GraphStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if node is None:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")
    return node


@app.get("/api/wiki/genes/{node_id:path}")
def gene_wiki(node_id: str) -> dict:
    try:
        result = get_graph_store().get_gene_wiki_record(node_id)
    except GraphStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if result["node"] is None:
        raise HTTPException(status_code=404, detail=f"Gene not found: {node_id}")
    return result


@app.get("/api/graph/neighbors/{node_id:path}")
def graph_neighbors(
    node_id: str,
    direction: Literal["in", "out", "both"] = Query(default="both"),
    predicate: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
) -> dict:
    try:
        result = get_graph_store().get_neighbors(
            node_id, direction=direction, predicate=predicate, limit=limit
        )
    except GraphStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if result["node"] is None:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")
    return result


@app.get("/api/graph/search")
def graph_search(
    q: str = Query(min_length=1),
    object_type: str | None = Query(default=None),
    species_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    try:
        nodes = get_graph_store().search_nodes(
            q, object_type=object_type, species_id=species_id, limit=limit
        )
    except GraphStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"query": q, "count": len(nodes), "nodes": nodes}


@app.get("/api/graph/species/{species_id}/genes")
def species_genes(
    species_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict:
    try:
        return get_graph_store().list_species_genes(
            species_id, limit=limit, offset=offset
        )
    except GraphStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

