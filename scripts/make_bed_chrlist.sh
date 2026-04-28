#!/bin/bash
set -eo pipefail

# ====================== 配置 ======================
SCRIPT_NAME=$(basename "$0")
PROJECT_DIR="/home/nizhu/Projects/plantsdb"
DEFAULT_INPUT_DIR="${PROJECT_DIR}/data/imp_gene_pos"
DEFAULT_OUTPUT_DIR="${PROJECT_DIR}/data/imp_gene_pos"

# ====================== 帮助 ======================
usage() {
    cat <<EOF
Usage: ./$SCRIPT_NAME [OPTIONS]

基于 imp_gene_pos 目录的 BED 文件，为 GeneTribe 生成 chrlist 文件

Options:
  -i, --input DIR    输入目录（包含 *.bed 文件）[默认: $DEFAULT_INPUT_DIR]
  -o, --output DIR   输出目录（chrlist 文件保存位置）[默认: $DEFAULT_INPUT_DIR]
  -h, --help         帮助

Output:
  每个 BED 文件对应生成同名的 *.chrlist 文件
  格式：染色体/contig 名称列表，每行一个，已去重排序

Example:
  ./$SCRIPT_NAME
  ./$SCRIPT_NAME -i ./data/imp_gene_pos -o ./data/imp_gene_pos
EOF
}

# ====================== 解析参数 ======================
INPUT_DIR=""
OUTPUT_DIR=""

while [[ $# -gt 0 ]]; do
    case "$1" in
    -i | --input)
        INPUT_DIR="$2"
        shift 2
        ;;
    -o | --output)
        OUTPUT_DIR="$2"
        shift 2
        ;;
    -h | --help)
        usage
        exit 0
        ;;
    *)
        echo "未知参数: $1"
        usage
        exit 1
        ;;
    esac
done

INPUT_DIR=${INPUT_DIR:-$DEFAULT_INPUT_DIR}
OUTPUT_DIR=${OUTPUT_DIR:-$DEFAULT_OUTPUT_DIR}

if [[ ! -d "$INPUT_DIR" ]]; then
    echo "错误：输入目录不存在 -> $INPUT_DIR"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "========================================"
echo "输入目录: $INPUT_DIR"
echo "输出目录: $OUTPUT_DIR"
echo "========================================"

# ====================== 生成 chrlist ======================
bed_count=0
for bed in "$INPUT_DIR"/*.bed; do
    [[ -f "$bed" ]] || continue
    sp=$(basename "$bed" .bed)
    output="${OUTPUT_DIR}/${sp}.chrlist"

    # 从 BED 第 2 列提取染色体/contig 名（该 BED 格式为: gene_id, chr, start, end, strand）
    cut -f2 "$bed" 2>/dev/null | sort -u | awk 'NF' >"$output"

    if [[ -s "$output" ]]; then
        lines=$(wc -l <"$output")
        echo "✅ ${sp}.chrlist ($lines 条)"
    else
        echo "⚠️  ${sp}.chrlist 为空（源文件: $bed）"
    fi
    ((bed_count++)) || true
done

echo -e "\n========================================"
echo "✅ 完成，共处理 $bed_count 个 BED 文件"
echo "========================================"
