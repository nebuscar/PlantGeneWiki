#!/bin/bash
# IMP data integration pipeline
# Integrates structure, sequence, properties, eggnog annotation, and homolog mapping

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$PROJECT_DIR")"

DEFAULT_INPUT_DIR="/DATA/data2/downloads/IMP"
DEFAULT_OUTPUT_DIR="${PROJECT_DIR}/result/result_imp"
MANIFEST="${PROJECT_DIR}/data/meta/imp/species_manifest.tsv"

SCRIPT_NAME=$(basename "$0")

usage() {
    cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS]

IMP data integration pipeline: structure, sequence, properties, eggnog, homolog.

Options:
  -i, --input DIR      Input IMP directory [default: $DEFAULT_INPUT_DIR]
  -o, --output DIR     Output directory [default: $DEFAULT_OUTPUT_DIR]
  -g, --genus          Enable genus grouping mode (homolog analysis)
  -m, --mode MODE      Run mode: all/structure/sequence/properties/eggnog/homolog [default: all]
  -s, --species NAME   Process only specified species
  -p, --prefix STR     Process only species starting with this prefix (e.g. B)
  -h, --help           Show this help

Examples:
  $SCRIPT_NAME -m all -g           # full pipeline with homolog
  $SCRIPT_NAME -m structure        # structure only
  $SCRIPT_NAME -m sequence,properties  # sequence and properties only
EOF
}

PARSED_ARGS=$(getopt -o hi:o:m:gs:p: --long help,input:,output:,mode:,genus,species:,prefix: --name "$0" -- "$@")
eval set -- "$PARSED_ARGS"

INPUT_DIR="$DEFAULT_INPUT_DIR"
OUTPUT_DIR="$DEFAULT_OUTPUT_DIR"
MODE="all"
GENUS_MODE=false
SPECIES=""
PREFIX=""

while true; do
    case "$1" in
    -i | --input)
        INPUT_DIR="$2"
        shift 2
        ;;
    -o | --output)
        OUTPUT_DIR="$2"
        shift 2
        ;;
    -m | --mode)
        MODE="$2"
        shift 2
        ;;
    -g | --genus)
        GENUS_MODE=true
        shift
        ;;
    -s | --species)
        SPECIES="$2"
        shift 2
        ;;
    -p | --prefix)
        PREFIX="$2"
        shift 2
        ;;
    -h | --help)
        usage
        exit 0
        ;;
    --)
        shift
        break
        ;;
    *)
        echo "Unknown option: $1"
        usage
        exit 1
        ;;
    esac
done

if [[ ! -d "$INPUT_DIR" ]]; then
    echo "Error: input directory not found: $INPUT_DIR"
    exit 1
fi

SPECIES_DIR="${OUTPUT_DIR}/species"
HOMOLOG_DIR="${OUTPUT_DIR}/homolog"
mkdir -p "$SPECIES_DIR" "$HOMOLOG_DIR"
# Resolve to absolute paths so heredocs and pushd/popd don't produce double-path bugs
SPECIES_DIR="$(cd "$SPECIES_DIR" && pwd)"
HOMOLOG_DIR="$(cd "$HOMOLOG_DIR" && pwd)"

echo "========================================"
echo "Input:       $INPUT_DIR"
echo "Species out: $SPECIES_DIR"
echo "Homolog out: $HOMOLOG_DIR"
echo "Mode:        $MODE"
[[ "$GENUS_MODE" == true ]] && echo "Genus:       enabled"
[[ -n "$SPECIES" ]] && echo "Species:     $SPECIES"
[[ -n "$PREFIX" ]] && echo "Prefix:      $PREFIX"
echo "========================================"

START_TIME=$(date +%s)

# Check dependencies
check_dep() {
    command -v "$1" &>/dev/null || {
        echo "Error: $1 not found"
        exit 1
    }
}
check_dep awk
check_dep seqkit
check_dep python3

# Discover species
discover_species() {
    local -a species_list=()
    for dir in "${INPUT_DIR}"/*/; do
        [[ -d "$dir" ]] || continue
        sp=$(basename "$dir")
        if [[ -n "$SPECIES" && "$sp" != "$SPECIES" ]]; then
            continue
        fi
        if [[ -n "$PREFIX" && "$sp" != "${PREFIX}"* ]]; then
            continue
        fi
        prefix=$(basename "$dir"/*.gff3.gz 2>/dev/null | head -1)
        prefix="${prefix%.gff3.gz}"
        if [[ -n "$prefix" && -f "$dir/${prefix}.prot.fasta" ]]; then
            species_list+=("$sp")
        fi
    done
    printf '%s\n' "${species_list[@]}" | sort
}

# Build mRNA → gene mapping from GFF3
build_mrna_gene_map() {
    local gff3="$1"
    zcat -f "$gff3" | awk -F'\t' '
$3 == "mRNA" {
    mrna = ""; gene = ""
    n = split($9, attrs, ";")
    for (i = 1; i <= n; i++) {
        if (attrs[i] ~ /^ID=/) {
            split(attrs[i], t, "="); mrna = t[2]
        }
        if (attrs[i] ~ /^Parent=/) {
            split(attrs[i], t, "="); gene = t[2]
        }
    }
    if (mrna && gene) print mrna "\t" gene
}
' | sort -u
}

# Discover genera from manifest
discover_genera() {
    local -A seen
    local -a genera=()
    while IFS=$'\t' read -r code name dir; do
        [[ "$code" == "Species_Code" ]] && continue
        [[ -z "$code" ]] && continue
        local genus="${name%% *}"
        [[ -n "$genus" && -z "${seen[$genus]:-}" ]] || continue
        seen[$genus]=1
        genera+=("$genus")
    done <"$MANIFEST"
    printf '%s\n' "${genera[@]}" | sort
}

# Get species belonging to a genus
get_species_in_genus() {
    local genus="$1"
    local -a species=()
    while IFS=$'\t' read -r code name dir; do
        [[ "$code" == "Species_Code" ]] && continue
        [[ -z "$code" ]] && continue
        local sp_genus="${name%% *}"
        [[ "$sp_genus" == "$genus" ]] || continue
        local sp_dir="${INPUT_DIR}/${dir}"
        if [[ -d "$sp_dir" ]] && compgen -G "$sp_dir/*.gff3.gz" >/dev/null 2>&1; then
            species+=("$dir")
        fi
    done <"$MANIFEST"
    printf '%s\n' "${species[@]}"
}

# ====================== Module 1: structure ======================
run_structure() {
    local sp="$1"
    local sp_dir="${INPUT_DIR}/${sp}"
    local out_dir="${SPECIES_DIR}/${sp}"
    local prefix=$(basename "$sp_dir"/*.gff3.gz | head -1)
    prefix="${prefix%.gff3.gz}"
    local gff3="${sp_dir}/${prefix}.gff3.gz"

    mkdir -p "$out_dir"

    zcat -f "$gff3" | awk -F'\t' -v OFS='\t' '
$3 == "gene" {
    mrna = ""; gene = ""
    n = split($9, attrs, ";")
    for (i = 1; i <= n; i++) {
        if (attrs[i] ~ /^ID=/) { split(attrs[i], t, "="); gene = t[2] }
    }
    if (gene) print gene, $1, $4, $5, $7
}' >"${out_dir}/${sp}.structure.tsv"
}

# ====================== Module 2: sequence ======================
run_sequence() {
    local sp="$1"
    local sp_dir="${INPUT_DIR}/${sp}"
    local out_dir="${SPECIES_DIR}/${sp}"
    local prefix=$(basename "$sp_dir"/*.gff3.gz | head -1)
    prefix="${prefix%.gff3.gz}"

    local mrna_gene_map=$(mktemp)
    build_mrna_gene_map "${sp_dir}/${prefix}.gff3.gz" >"$mrna_gene_map"

    local remap_awk='
BEGIN { while ((getline < map) > 0) m[$1] = $2 }
/^>/ {
    split(substr($0,2), arr, /[ \t]/)
    mrna = arr[1]
    gene = (mrna in m) ? m[mrna] : mrna
    print ">" gene "|" mrna
    next
}
{ print }'

    # protein_seq
    if [[ -s "${sp_dir}/${prefix}.prot.fasta" ]]; then
        awk -v map="$mrna_gene_map" "$remap_awk" \
            "${sp_dir}/${prefix}.prot.fasta" >"${out_dir}/${sp}.protein.fa"
    fi

    # cds_seq
    if [[ -s "${sp_dir}/${prefix}.CDS.fasta" ]]; then
        awk -v map="$mrna_gene_map" "$remap_awk" \
            "${sp_dir}/${prefix}.CDS.fasta" >"${out_dir}/${sp}.cds.fa"
    fi

    # gene_seq
    if [[ -s "${sp_dir}/${prefix}.gene.fasta" ]]; then
        cp "${sp_dir}/${prefix}.gene.fasta" "${out_dir}/${sp}.gene.fa"
    fi

    rm "$mrna_gene_map"
}

# ====================== Module 3: properties ======================
run_properties() {
    local sp="$1"
    local sp_dir="${INPUT_DIR}/${sp}"
    local out_dir="${SPECIES_DIR}/${sp}"

    python3 - <<EOF
import sys
import os
from Bio import SeqIO
from Bio.SeqUtils.ProtParam import ProteinAnalysis

sp = "$sp"
out_dir = "$out_dir"
sp_dir = "$sp_dir"

prefix = [f for f in os.listdir(sp_dir) if f.endswith('.gff3.gz')][0]
prefix = prefix[:-8]

prot_file = os.path.join(sp_dir, prefix + '.prot.fasta')

# skip if prot.fasta is missing or empty
if not os.path.isfile(prot_file) or os.path.getsize(prot_file) == 0:
    sys.exit(0)

mrna_gene = {}

import gzip
with gzip.open(os.path.join(sp_dir, prefix + '.gff3.gz'), 'rt') as f:
    for line in f:
        if line.startswith('#'):
            continue
        fields = line.strip().split('\t')
        if len(fields) < 9 or fields[2] != 'mRNA':
            continue
        mrna = gene = None
        for attr in fields[8].split(';'):
            if attr.startswith('ID='):
                mrna = attr[3:]
            if attr.startswith('Parent='):
                gene = attr[7:]
        if mrna and gene:
            mrna_gene[mrna] = gene

results = []
for record in SeqIO.parse(prot_file, 'fasta'):
    mrna_id = record.id
    gene_id = mrna_gene.get(mrna_id, mrna_id)
    seq = str(record.seq).replace('*', '').strip()
    length = len(seq)
    if length == 0:
        results.append([gene_id, mrna_id, length, '', ''])
        continue
    try:
        prot = ProteinAnalysis(seq)
        pi = round(prot.isoelectric_point(), 4)
        mw = round(prot.molecular_weight(), 2)
    except:
        pi = mw = ''
    results.append([gene_id, mrna_id, length, pi, mw])

# only write output if there are actual data rows
if not results:
    sys.exit(0)

out_path = os.path.join(out_dir, sp + '.properties.tsv')
with open(out_path, 'w') as f:
    f.write('gene_id\tmRNA_id\tprotein_length\tisoelectric_point\tmolecular_weight\n')
    for row in results:
        f.write('\t'.join(str(x) for x in row) + '\n')
EOF
}

# ====================== Module 4: eggnog ======================
run_eggnog() {
    local sp="$1"
    local sp_dir="${INPUT_DIR}/${sp}"
    local out_dir="${SPECIES_DIR}/${sp}"
    local prefix=$(basename "$sp_dir"/*.gff3.gz | head -1)
    prefix="${prefix%.gff3.gz}"

    [[ -f "${out_dir}/${sp}.eggnog.tsv" ]] && {
        echo "  skip (done)"
        return
    }
    [[ -s "${sp_dir}/${prefix}.prot.fasta" ]] || {
        echo "  skip (no prot)"
        return
    }

    local work_dir="${out_dir}/eggnog_work"
    mkdir -p "$work_dir"

    # Build mRNA -> gene mapping
    local mrna_gene_map=$(mktemp)
    build_mrna_gene_map "${sp_dir}/${prefix}.gff3.gz" >"$mrna_gene_map"

    # Run emapper
    source /home/nizhu/software/miniforge3/etc/profile.d/conda.sh
    conda activate biotools

    python3 /home/nizhu/software/miniforge3/envs/biotools/bin/emapper.py \
        -i "${sp_dir}/${prefix}.prot.fasta" \
        -o "${work_dir}/${sp}" \
        --data_dir /DATA/data2/emapperdb-5.0.2 \
        -m mmseqs \
        --cpu 40 \
        --dbmem \
        --tax_scope auto \
        --override \
        --no_file_comments 2>/dev/null

    # Parse and convert mRNA ID to gene ID
    python3 - <<EOF
import re
import os

sp = "$sp"
work_dir = "$work_dir"
out_dir = "$out_dir"
mrna_gene_map = "$mrna_gene_map"

# Load mRNA -> gene mapping
mrna_to_gene = {}
with open(mrna_gene_map) as f:
    for line in f:
        parts = line.strip().split('\t')
        if len(parts) == 2:
            mrna_to_gene[parts[0]] = parts[1]

annot_file = os.path.join(work_dir, sp + '.emapper.annotations')
if not os.path.exists(annot_file):
    print(f"Warning: annotation file not found: {annot_file}")
    exit(1)

results = []
with open(annot_file) as f:
    for line in f:
        if line.startswith('#') or line.startswith('query'):
            continue
        line = line.strip()
        if not line:
            continue
        fields = line.split('\t')
        if len(fields) < 12:
            continue

        query = fields[0]
        gene_id = mrna_to_gene.get(query, query)
        description = fields[7] if len(fields) > 7 else ''
        go_terms = re.sub(r'@.*', '', fields[9]) if len(fields) > 9 else ''
        kegg = re.sub(r'@.*', '', fields[12]) if len(fields) > 12 else ''
        pfam = fields[20] if len(fields) > 20 else ''

        results.append([gene_id, query, go_terms, kegg, pfam, description])

out_path = os.path.join(out_dir, sp + '.eggnog.tsv')
with open(out_path, 'w') as f:
    f.write('gene_id\tmRNA_id\tGO\tKEGG\tPfam\tDescription\n')
    for row in results:
        f.write('\t'.join(str(x) for x in row) + '\n')
EOF

    rm "$mrna_gene_map"
}

# ====================== Module 5: homolog ======================
run_homolog() {
    local genus="$1"
    local genus_dir="${HOMOLOG_DIR}/${genus}"
    mkdir -p "$genus_dir"
    cd "$genus_dir"

    local -a species=($(get_species_in_genus "$genus"))
    if [[ ${#species[@]} -lt 2 ]]; then
        echo "  Skipping $genus: less than 2 species"
        return
    fi

    echo "  Homolog: $genus (${#species[@]} species)"

    # Prepare files for each species
    for sp in "${species[@]}"; do
        sp_dir="${INPUT_DIR}/${sp}"
        prefix=$(basename "$sp_dir"/*.gff3.gz | head -1)
        prefix="${prefix%.gff3.gz}"

        # Build mRNA->gene map and write gene-ID faa
        local mrna_gene_map
        mrna_gene_map=$(mktemp)
        build_mrna_gene_map "${sp_dir}/${prefix}.gff3.gz" >"$mrna_gene_map"
        # Remove any existing symlink before writing to avoid following it and corrupting the target
        [[ -L "${sp}.faa" ]] && rm -f "${sp}.faa"
        awk -v map="$mrna_gene_map" '
BEGIN { while ((getline < map) > 0) m[$1] = $2 }
/^>/ {
    split(substr($0,2), arr, /[ \t]/)
    mrna = arr[1]
    gene = (mrna in m) ? m[mrna] : mrna
    print ">" gene
    next
}
{ print }
' "${sp_dir}/${prefix}.prot.fasta" >"${sp}.faa"
        rm "$mrna_gene_map"

        # BED
        [[ -L "${sp}.bed" ]] && rm -f "${sp}.bed"
        zcat -f "${sp_dir}/${prefix}.gff3.gz" | awk -F'\t' -v OFS='\t' '
$3 == "gene" {
    gene = ""
    n = split($9, attrs, ";")
    for (i = 1; i <= n; i++) {
        if (attrs[i] ~ /^ID=/) { split(attrs[i], t, "="); gene = t[2] }
    }
    if (gene) print $1, $4-1, $5, gene, ".", $7
}' >"${sp}.bed"

        # chrlist
        [[ -L "${sp}.chrlist" ]] && rm -f "${sp}.chrlist"
        cut -s -f1 "${sp}.bed" | sort -u >"${sp}.chrlist"
    done

    # Select reference species: longest protein length among species with valid chrlist (>=2 chromosomes)
    local ref_sp=""
    local max_len=0
    for sp in "${species[@]}"; do
        # Skip species with empty/single-entry chrlist (no chromosome info — jcvi will fail)
        local nchr
        nchr=$(awk 'NF>0' "${sp}.chrlist" 2>/dev/null | wc -l)
        if [[ $nchr -lt 2 ]]; then
            echo "    Warning: $sp has $nchr valid chromosomes, skipping as ref candidate"
            continue
        fi
        len=$(awk '/^>/{next} {len+=length($0)} END{print len}' "$sp.faa")
        if [[ $len -gt $max_len ]]; then
            max_len=$len
            ref_sp=$sp
        fi
    done
    # Fallback: if no species passed chrlist filter, use longest regardless
    if [[ -z "$ref_sp" ]]; then
        for sp in "${species[@]}"; do
            len=$(awk '/^>/{next} {len+=length($0)} END{print len}' "$sp.faa")
            if [[ $len -gt $max_len ]]; then
                max_len=$len
                ref_sp=$sp
            fi
        done
        echo "    Warning: no species with valid chrlist, using $ref_sp as fallback ref"
    fi
    echo "    Reference: $ref_sp"

    # Run genetribe for each query species (requires genetribe conda env for jcvi)
    # Use local /tmp to avoid NFS silly-rename issues with genetribe_output/
    source /home/nizhu/software/miniforge3/etc/profile.d/conda.sh
    conda activate genetribe

    local gt_tmp
    gt_tmp=$(mktemp -d /tmp/genetribe_XXXXXX)

    # Sanitize species names for genetribe:
    # jcvi/tribemath treats "." as a delimiter and "._" as variant separator.
    # We must preserve "var._SantaCruz_75_HAP1" as one variant token, so we
    # replace "." with "+" which is not used as a delimiter by genetribe/jcvi.
    sanitize_gt() { echo "$1" | sed 's/\./+/g'; }

    # Symlink all faa/bed/chrlist files into the local tmp dir (with sanitized names)
    # Use same sanitization as genetribe calls (replace "." with "+")
    for f in "${genus_dir}"/*.faa "${genus_dir}"/*.bed "${genus_dir}"/*.chrlist; do
        [[ -f "$f" ]] || continue
        base=$(basename "$f")
        # Extract extension, sanitize name, then restore extension
        ext="${base##*.}"
        name="${base%.*}"
        san_name=$(echo "$name" | sed 's/\./+/g')
        san_base="${san_name}.${ext}"
        ln -sf "$f" "${gt_tmp}/${san_base}"
    done

    # query species list: exclude ref and species with invalid chrlist
    local -a query_species=()
    for sp in "${species[@]}"; do
        [[ "$sp" == "$ref_sp" ]] && continue
        local nchr
        nchr=$(awk 'NF>0' "${sp}.chrlist" 2>/dev/null | wc -l)
        if [[ $nchr -lt 2 ]]; then
            echo "    Skipping query $sp: invalid chrlist ($nchr chromosomes)"
            continue
        fi
        query_species+=("$sp")
    done

    if [[ ${#query_species[@]} -eq 0 ]]; then
        echo "  Skipping $genus: no valid query species after chrlist filter"
        rm -rf "$gt_tmp"
        conda deactivate
        return
    fi

    local san_ref_sp
    san_ref_sp=$(sanitize_gt "$ref_sp")

    for sp in "${query_species[@]}"; do
        local san_sp
        san_sp=$(sanitize_gt "$sp")
        pushd "$gt_tmp" >/dev/null
        rm -rf genetribe_output/
        genetribe core -l "$san_ref_sp" -f "$san_sp" -n 80 >/dev/null 2>&1
        # Copy RBH result (genetribe names it using sanitized names; store with original names)
        [[ -f "${san_ref_sp}_${san_sp}.RBH" ]] && cp "${san_ref_sp}_${san_sp}.RBH" "${genus_dir}/${ref_sp}_${sp}.RBH"
        popd >/dev/null
    done
    rm -rf "$gt_tmp"
    conda deactivate

    # Build merged matrix: ref_gene -> one column per query species
    python3 - <<EOF
import os

genus_dir = "$genus_dir"
genus = "$genus"
ref_sp = "$ref_sp"
query_species = """${query_species[*]}""".split()

# Load RBH pairs for each query species: ref_gene -> query_gene
sp_maps = {}
for sp in query_species:
    rbh_file = os.path.join(genus_dir, f"{ref_sp}_{sp}.RBH")
    m = {}
    if os.path.isfile(rbh_file):
        with open(rbh_file) as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    m[parts[0]] = parts[1]
    sp_maps[sp] = m

# Collect all ref genes that appear in at least one query
all_ref_genes = set()
for m in sp_maps.values():
    all_ref_genes.update(m.keys())

out_path = os.path.join(genus_dir, f"{genus}_homolog_1v1.tsv")
with open(out_path, 'w') as f:
    # Header: ref species name as first column, then each query species name
    header = ref_sp + '\t' + '\t'.join(query_species)
    f.write(header + '\n')
    for ref_gene in sorted(all_ref_genes):
        row = [ref_gene] + [sp_maps[sp].get(ref_gene, '-') for sp in query_species]
        f.write('\t'.join(row) + '\n')

total = len(all_ref_genes)
print(f"  ref genes with RBH: {total}, queries: {len(query_species)}")
EOF
}

# ====================== Run pipeline ======================
IFS=$'\n' read -d '' -a SPECIES_LIST < <(discover_species) || true

if [[ ${#SPECIES_LIST[@]} -eq 0 ]]; then
    echo "No species found"
    exit 1
fi

echo "Found ${#SPECIES_LIST[@]} species"
echo ""

# Run per-species modules (1-4)
for sp in "${SPECIES_LIST[@]}"; do
    echo "[$sp]"
    sp_dir="${INPUT_DIR}/${sp}"

    mkdir -p "${SPECIES_DIR}/${sp}"

    IFS=',' read -ra modes <<<"$MODE"
    for m in "${modes[@]}"; do
        case "$m" in
        all | structure) run_structure "$sp" ;;
        all | sequence) run_sequence "$sp" ;;
        all | properties) run_properties "$sp" ;;
        all | eggnog) run_eggnog "$sp" ;;
        esac
    done
done

# Run homolog (per genus)
if $GENUS_MODE; then
    echo ""
    echo "Homolog analysis..."

    IFS=$'\n' read -d '' -a GENERA_LIST < <(discover_genera) || true

    for genus in "${GENERA_LIST[@]}"; do
        species_in_genus=($(get_species_in_genus "$genus"))
        if [[ ${#species_in_genus[@]} -lt 2 ]]; then
            continue
        fi
        # Only process genera that have species in our list
        has_species=false
        for sp in "${species_in_genus[@]}"; do
            for s in "${SPECIES_LIST[@]}"; do
                if [[ "$sp" == "$s" ]]; then
                    has_species=true
                    break 2
                fi
            done
        done
        if $has_species; then
            run_homolog "$genus"
        fi
    done
fi

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
echo ""
echo "========================================"
echo "Done in ${ELAPSED}s"
echo "Species: $SPECIES_DIR"
echo "Homolog: $HOMOLOG_DIR"
echo "========================================"
