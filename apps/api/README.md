# PlantGeneWiki API

FastAPI service for querying PlantGeneWiki graph indexes.

## Local server

FastAPI version:

```bash
cd apps/api
export PLANTGENEWIKI_GRAPH_DB=/DATA/data2/plantgenewiki/graph/pgcp_v1/plantgenewiki_pgcp_v1.sqlite
uvicorn plantgenewiki_api.main:app --host 0.0.0.0 --port 8001
```

Dependency-free server version:

```bash
cd apps/api
python3 -m plantgenewiki_api.simple_server --host 0.0.0.0 --port 8001
```

## Endpoints

- `GET /api/health`
- `GET /api/graph/summary`
- `GET /api/graph/nodes/{node_id}`
- `GET /api/graph/neighbors/{node_id}?direction=both&limit=50`
- `GET /api/graph/search?q=Atha01G0000010&limit=20`
- `GET /api/graph/species/{species_id}/genes?limit=50&offset=0`
