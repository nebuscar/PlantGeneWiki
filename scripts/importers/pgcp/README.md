# PGCP Importer Scripts

This directory keeps only the currently maintained PGCP acquisition entry point that is still covered by tests. Older PGCP crawl, metadata, download, ortholog extraction, and batch migration scripts have been moved to `archive/pgcp/importers/`.

PGCP is treated as a source system. Normalized downstream processing should consume Dataset, Knowledge Object, Relation, and EvidenceClaim records rather than depend on the old PGCP directory layout.

## Layout

```text
scripts/importers/pgcp/
|-- gene_records/      # maintained per-gene JSON downloader
`-- README.md
```

## Active Entry Points

- `gene_records/download_pgcp_gene_json.py`: resumable per-gene JSON downloader, retained because it is tested and documents the current PGCP raw JSON acquisition behavior.

## Archived Scripts

Historical scripts are archived under:

```text
archive/pgcp/importers/
|-- download/
|-- metadata/
|-- legacy_batches/
|-- pgcp_orthologs.py
`-- run_pgcp_atha_json.sh
```

Use archived scripts as references only. New work should prefer reusable `src/plantgenewiki/` tools and normalized Dataset / Knowledge Object outputs.

## Test Command

From the project root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -v tests
```
