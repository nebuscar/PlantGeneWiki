# Gene Wiki Browser Smoke Test

## Purpose

Confirm that rich and sparse Arabidopsis Gene Wiki records render as readable, complete pages against the production SQLite snapshot.

## Start the services

Terminal 1:

```bash
cd /home/nizhu/Projects/PhytoAtlas/apps/api
PHYTOATLAS_GRAPH_DB=/DATA/data2/phytoatlas/graph/pgcp_v1/phytoatlas_pgcp_v1.sqlite uvicorn phytoatlas_api.main:app --host 0.0.0.0 --port 8000
```

Terminal 2:

```bash
cd /home/nizhu/Projects/PhytoAtlas/apps/web
VITE_API_BASE=http://127.0.0.1:8000 npm run dev
```

## Test records

- Rich: `http://localhost:4322/genes/Atha04G0031690.v1.36`
- Sparse: `http://localhost:4322/genes/Atha01G0000130.v1.36`

## Acceptance checklist

- The left section navigation remains visible and selects all nine permanent sections.
- Overview, Identifiers, Location, Structure, Function, Sequences, Homology, Evidence, and Publications are present.
- Location fields show assembly, coordinates, strand, and coordinate system.
- Rich Structure shows 27 transcripts.
- Rich Sequences shows 27 CDS and 27 Protein records with working links.
- Sparse Structure shows one transcript, one CDS, and one Protein record.
- Homology and Publications show `Not available` when source datasets are absent.
- No raw JSON, `[object Object]`, `source_file`, or internal server paths are visible.
- Browser console and network panel contain no page-load errors.

Record the date, graph snapshot, URLs, and PASS/FAIL result in `docs/architecture/arabidopsis-mvp-acceptance.md`.
