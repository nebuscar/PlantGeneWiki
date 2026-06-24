# Developer Guide

## Project Layout

PlantGeneWiki follows a product-style project layout:

- apps/: runnable applications built on top of PlantGeneWiki.
- apps/agent/: current Chainlit-based agent prototype.
- src/: reusable PlantGeneWiki core library code.
- scripts/: command-line entry points for data collection, cleaning, builds, and maintenance.
- scripts/importers/: preferred location for source-specific acquisition and import entry points.
- scripts/importers/pgcp/: current PGCP source-specific importer scripts.
- scripts/analysis/msa/: MSA toolkit scripts.
- scripts/analysis/structure/: ESMFold and Foldseek structure tools.
- scripts/services/: service management entry points.
- scripts/maintenance/: maintenance and migration utilities.
- data/: ignored local/remote data workspace.
- docs/: source notes, user/developer documentation, maintenance records.
- tests/: unit and smoke tests.
- config/: public configuration templates and source mappings.
- deploy/: deployment notes and service definitions.

## Standardized Data Boundary

Treat PGCP, NCBI, BRAD, literature collections, and archived IMP materials as sources or batches. Store source and batch details inside Dataset, Provenance, and EvidenceClaim records. Downstream builders should consume standardized objects, relations, and evidence records instead of branching on source-specific folder names.

See docs/data/standardized_data_model.md for the current design.

## PGCP Raw JSON Downloader

Primary script:

```bash
python3 scripts/importers/pgcp/gene_records/download_pgcp_gene_json.py arabidopsis_thaliana \
  --expected-count 27655 \
  --workers 2 \
  --delay 0.5 \
  --timeout 120 \
  --retries 5 \
  --output-dir data/pgcp_ortho/arabidopsis_thaliana_json
```

The downloader:

- fetches the species gene list from PGCP `genome` API;
- writes one raw JSON per gene into `raw/`;
- uses `.part` files plus atomic rename to avoid corrupt partial JSON;
- skips existing complete JSON files on rerun;
- records failed genes in `failures.tsv`.

## PGCP Health Check

Before starting a new crawl, run a single-gene check:

```bash
curl -sS -o /tmp/pgcp_gene_check.json \
  --connect-timeout 10 \
  --max-time 60 \
  -H 'x-requested-with: XMLHttpRequest' \
  'https://biobigdata.nju.edu.cn/pgdatabaseAPI/gene?species=arabidopsis_thaliana&gene=Atha01G0000010.v1.36' \
  -w 'code=%{http_code} size=%{size_download} total=%{time_total}\n'
```

Only start batch crawling when the status code is `200`.

## Running Tests

```bash
python3 -m unittest -v tests/pgcp/test_download_pgcp_gene_json.py
```

## Git Hygiene

Do not commit large raw data. Keep generated data under `data/` and document paths in `docs/data_sources.md` or `data/README.md`.
