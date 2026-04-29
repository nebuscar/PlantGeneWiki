#!/bin/bash
# 从IMP的gff3.gz文件提取gene位置信息
# 输出: gene_id, chrom, start, end, strand

set -e

usage() {
    echo "用法: $0 <gff3.gz文件或包含gff3.gz的目录> [输出目录]"
    exit 1
}

[[ $# -lt 1 ]] && usage

INPUT="$1"
OUTDIR="${2:-/home/nizhu/Projects/plantsdb/data/imp_gene_pos}"

mkdir -p "$OUTDIR"

extract_gff() {
    local gff="$1"
    local base=$(basename "$gff" .gff3.gz)
    local outfile="${OUTDIR}/${base}.bed"
    if [[ -f "$outfile" ]]; then
        echo "跳过(已存在): $outfile"
        return 0
    fi
    zcat -f "$gff" | awk -F'\t' -v OFS='\t' '
        $3 == "gene" {
            if (match($9, /ID=([^;]+)/, arr)) {
                print arr[1], $1, $4, $5, $7
            }
        }
    ' > "$outfile"
    echo "生成: $outfile"
}

if [[ -f "$INPUT" ]]; then
    extract_gff "$INPUT"
elif [[ -d "$INPUT" ]]; then
    find "$INPUT" -name "*.gff3.gz" -type f | while read gff; do
        extract_gff "$gff"
    done
else
    echo "错误: $INPUT 不是文件也不是目录"
    exit 1
fi
