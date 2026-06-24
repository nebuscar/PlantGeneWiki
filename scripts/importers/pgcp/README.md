# PGCP Importer Scripts

This directory contains PGCP-specific acquisition and import entry points. PGCP is treated as a source system; normalized downstream processing should consume Dataset, Knowledge Object, Relation, and EvidenceClaim records rather than this directory layout.

## Layout

```text
scripts/importers/pgcp/
|-- download/          # PGCP file download API utilities
|-- metadata/          # species lists, download metadata, genome endpoint snapshots
|-- gene_records/      # per-gene JSON and ortholog record collection
|-- legacy_batches/    # historical batch scripts and migration helpers
`-- README.md
```

PGCP-derived but generally analytical workflows live under scripts/analysis/, for example enrichment and primer design.

## Active Entry Points

- gene_records/download_pgcp_gene_json.py: resumable per-gene JSON downloader.
- gene_records/run_pgcp_atha_json.sh: Arabidopsis thaliana wrapper for the gene JSON downloader.
- gene_records/pgcp_orthologs.py: batch ortholog table extraction from PGCP gene records.
- download/download_api.py: PGCP file download API utility.
- metadata/scrape_biobigdata.py: PGCP download metadata scraper.
- metadata/crawl_pgcp_data.py: PGCP species metadata crawler.

## Legacy Or Batch-Specific Files

- legacy_batches/download_batch.sh and legacy_batches/download_batch2.sh are historical batch download scripts.
- legacy_batches/copy_pgcp_genes.py copies old PGCP gene outputs into external genome storage. Treat it as a migration helper, not a standard pipeline step.
- metadata/fetch_pgcp.sh is a generated-style endpoint snapshot script. Prefer structured metadata crawlers for new work.

## Test Command

From the project root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -v tests
```
