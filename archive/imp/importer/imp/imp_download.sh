#!/bin/bash
# IMP batch download: crawl species list then download genome data

set -uo pipefail

PROJECT_DIR="/home/nizhu/Projects/PlantGeneWiki"
CRAWLER_DIR="${PROJECT_DIR}/scripts/importers/imp/imp_crawler"
DOWNLOAD_DIR="/DATA/data2/downloads/IMP"
LOG_DIR="${DOWNLOAD_DIR}/logs"

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Options:
  -o, --outdir DIR     Download directory [default: $DOWNLOAD_DIR]
  -m, --manifest FILE  Species manifest TSV/JSON
  -s, --species NAME   Single species dir_name (for testing)
  -l, --limit NUM      Limit number of species
  -t, --threads NUM    Parallel download threads [default: 4]
  -d, --dry-run        Show URLs without downloading
      --no-skip        Re-download already existing files
      --list           Crawl species list only, no download
  -h, --help           Show this help
EOF
}

MANIFEST=""
SPECIES=""
PREFIX=""
LIMIT=""
THREADS=4
DRY_RUN=""
NO_SKIP=""
LIST_ONLY=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        -o|--outdir)   DOWNLOAD_DIR="$2"; shift 2 ;;
        -m|--manifest) MANIFEST="$2"; shift 2 ;;
        -s|--species)  SPECIES="$2"; shift 2 ;;
        -p|--prefix)   PREFIX="$2"; shift 2 ;;
        -l|--limit)    LIMIT="--limit $2"; shift 2 ;;
        -t|--threads)  THREADS="$2"; shift 2 ;;
        -d|--dry-run)  DRY_RUN="--dry-run"; shift ;;
        --no-skip)     NO_SKIP="--no-skip"; shift ;;
        --list)        LIST_ONLY=true; shift ;;
        -h|--help)     usage; exit 0 ;;
        *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
done

LOG_DIR="${DOWNLOAD_DIR}/logs"
mkdir -p "$DOWNLOAD_DIR" "$LOG_DIR"

echo "outdir: $DOWNLOAD_DIR"

# Step 1: crawl species list
if $LIST_ONLY; then
    python3 "${CRAWLER_DIR}/species_crawler.py"
    exit 0
fi

# crawl fresh list if no manifest provided and default doesn't exist
DEFAULT_MANIFEST="${PROJECT_DIR}/data/meta/imp/species_manifest.tsv"
if [[ -z "$MANIFEST" && ! -f "$DEFAULT_MANIFEST" ]]; then
    echo "no manifest found, crawling species list..."
    python3 "${CRAWLER_DIR}/species_crawler.py"
fi

# Step 2: download
MANIFEST_ARG=""
[[ -n "$MANIFEST" ]] && MANIFEST_ARG="--manifest $MANIFEST"

SPECIES_ARG=""
[[ -n "$SPECIES" ]] && SPECIES_ARG="--species $SPECIES"

PREFIX_ARG=""
[[ -n "$PREFIX" ]] && PREFIX_ARG="--prefix $PREFIX"

python3 "${CRAWLER_DIR}/download_manager.py" \
    --outdir "$DOWNLOAD_DIR" \
    --logdir "$LOG_DIR" \
    --threads "$THREADS" \
    $MANIFEST_ARG $SPECIES_ARG $PREFIX_ARG $LIMIT $DRY_RUN $NO_SKIP

echo "done. logs: $LOG_DIR"
