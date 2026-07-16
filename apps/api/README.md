# PhytoAtlas API

FastAPI service for graph-backed PhytoAtlas object search and neighborhood queries.

## Environment

```bash
export PHYTOATLAS_GRAPH_DB=/DATA/data2/phytoatlas/graph/pgcp_v1/phytoatlas_pgcp_v1.sqlite
export PHYTOATLAS_CORS_ORIGINS=http://localhost:5173
```

## Run

From `apps/api`:

```bash
uvicorn phytoatlas_api.main:app --reload --host 0.0.0.0 --port 8000
```

The dependency-free fallback server remains available:

```bash
python -m phytoatlas_api.simple_server --host 0.0.0.0 --port 8001
```

## Verify

```bash
python -m compileall -q phytoatlas_api
python -m unittest discover -s tests -v
```

## Stable endpoints

- `GET /api/health`
- `GET /api/graph/search`
- `GET /api/graph/nodes/{node_id}`
- `GET /api/graph/neighbors/{node_id}`
- `GET /api/graph/species/{species_id}/genes`
