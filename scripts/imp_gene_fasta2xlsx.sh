#!/bin/bash
# 从IMP的gene.fasta提取基因序列，输出xlsx(两列: gene_id, genome)

set -e

usage() {
    echo "用法: $0 <gene.fasta文件或包含gene.fasta的目录> [输出目录]"
    exit 1
}

[[ $# -lt 1 ]] && usage

INPUT="$1"
OUTDIR="${2:-/home/nizhu/Projects/plantsdb/data/imp_gene_seq}"

mkdir -p "$OUTDIR"

extract_seq() {
    local fasta="$1"
    local base=$(basename "$fasta" .fasta | sed 's/\.gene//')
    local outfile="${OUTDIR}/${base}.xlsx"
    if [[ -f "$outfile" ]]; then
        echo "跳过(已存在): $outfile"
        return 0
    fi

    ~/software/miniforge3/envs/biotools/bin/python3 - <<EOF
import sys
from collections import OrderedDict

fasta = "$fasta"
outfile = "$outfile"

seqs = OrderedDict()
curr_id = None
curr_seq = []

with open(fasta, 'r') as fh:
    for line in fh:
        line = line.rstrip()
        if line.startswith('>'):
            if curr_id:
                seqs[curr_id] = ''.join(curr_seq)
            curr_id = line[1:]
            curr_seq = []
        else:
            curr_seq.append(line)
    if curr_id:
        seqs[curr_id] = ''.join(curr_seq)

try:
    import openpyxl
except ImportError:
    print("需要安装openpyxl: pip install openpyxl", file=sys.stderr)
    sys.exit(1)

wb = openpyxl.Workbook()
ws = wb.active
ws.append(['gene_id', 'genome'])
for gid, gseq in seqs.items():
    ws.append([gid, gseq])

wb.save(outfile)
print(f"生成: {outfile}")
EOF
}

if [[ -f "$INPUT" ]]; then
    extract_seq "$INPUT"
elif [[ -d "$INPUT" ]]; then
    find "$INPUT" -name "*.gene.fasta" -type f | while read f; do
        extract_seq "$f"
    done
else
    echo "错误: $INPUT 不是文件也不是目录"
    exit 1
fi
