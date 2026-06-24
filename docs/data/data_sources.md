# Data Sources

PlantGeneWiki uses external data sources as evidence layers for a plant genomics knowledge agent. Data integration is not the final objective; it supports evidence-traceable retrieval, structured knowledge graph queries, and LLM-assisted reasoning in complex crop genomics.

The current research focus is rapeseed and related plant genomics knowledge, including literature evidence, gene annotations, expression profiles, homolog relationships, GO/KEGG terms, cultivar records, and structured trait associations.

## PGCP

- Site: https://biobigdata.nju.edu.cn/pgdatabase/
- API base used by maintenance scripts:
  - `https://biobigdata.nju.edu.cn/pgdatabaseAPI/genome?species=<species>`
  - `https://biobigdata.nju.edu.cn/pgdatabaseAPI/gene?species=<species>&gene=<gene>`
- Current raw JSON storage:
  - Local raw snapshots are stored outside the public web app and referenced through Dataset registry metadata.
- Current Arabidopsis thaliana snapshot:
  - `26802 / 27655` raw gene JSON files were captured before the PGCP API outage.
  - Missing records are documented in `failures.tsv` and round-specific failure backups.

Operational note: PGCP API became unstable after the Arabidopsis run and returned HTTP 500 / timeouts. Do not start new bulk crawls until a single-gene API check returns HTTP 200.

## IMP

IMP is not part of the current active workflow. Related scripts and notes are archived under:

- `archive/imp/`
- `archive/docs/imp/`

Historical data references such as `data/meta/imp/` may exist locally, but `data/` is ignored by Git.

## NCBI

NCBI-related material is currently historical/reference material rather than an active crawl target. Archived notes remain under `docs/archive/ncbi/`. No active `scripts/ncbi/` entry point is maintained in the current project structure.

## Data Placement Policy

Large external data stays under `data/` and is not committed to Git unless explicitly curated as a small fixture.

- `data/raw/`: raw external downloads and snapshots.
- `data/processed/`: cleaned tables, derived TSV/CSV/JSON/Parquet.
- `data/database/`: SQLite, DuckDB, vector indexes, search indexes, or database dumps.
- `data/pgcp_ortho/`: existing PGCP orthology/raw JSON workspace retained for compatibility with current scripts.
