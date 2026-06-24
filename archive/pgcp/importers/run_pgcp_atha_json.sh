#!/usr/bin/env bash
set -u

PROJECT_DIR="/home/nizhu/Projects/PlantGeneWiki"
OUTPUT_DIR="$PROJECT_DIR/data/pgcp_ortho/arabidopsis_thaliana_json"

cd "$PROJECT_DIR" || exit 1
exec python3 scripts/importers/pgcp/gene_records/download_pgcp_gene_json.py arabidopsis_thaliana \
  --expected-count 27655 \
  --workers 2 \
  --delay 0.5 \
  --timeout 120 \
  --retries 5 \
  --output-dir "$OUTPUT_DIR" \
  >>"$OUTPUT_DIR/run.log" \
  2>>"$OUTPUT_DIR/run.err.log"
