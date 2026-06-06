#!/bin/bash
# 清理物种信息表中的多余空格
# 功能：清理 Species 和 Accession name 列中的多余空格

set -euo pipefail

# 默认路径
DEFAULT_INPUT="/home/nizhu/Projects/plantsdb/data/meta/ncbi/species_list_unique_with_taxid.txt"
DEFAULT_OUTPUT="/home/nizhu/Projects/plantsdb/data/meta/ncbi/species_list_cleaned.tsv"

INPUT_FILE=""
OUTPUT_FILE=""

# 显示帮助
show_help() {
    cat <<EOF
用法: $(basename "$0") [选项]

功能:
  清理物种信息表中的多余空格
  - 清理 Species 列（第2列）中的多余空格
  - 清理 Accession name 列（第5列）中的多余空格

选项:
  -h, --help              显示帮助信息
  -i, --input FILE        输入文件路径 (默认: ${DEFAULT_INPUT})
  -o, --output FILE       输出文件路径 (默认: ${DEFAULT_OUTPUT})

示例:
  $(basename "$0") -i species.xlsx -o cleaned.tsv
  $(basename "$0")  # 使用默认路径
EOF
    exit 0
}

# # 无参数时显示帮助
# if [[ $# -eq 0 ]]; then
#     show_help
# fi

# 解析参数
while [[ $# -gt 0 ]]; do
    case "$1" in
    -h | --help) show_help ;;
    -i | --input)
        INPUT_FILE="$2"
        shift 2
        ;;
    -o | --output)
        OUTPUT_FILE="$2"
        shift 2
        ;;
    *)
        echo "未知选项: $1"
        show_help
        ;;
    esac
done

# 设置默认值
INPUT_FILE="${INPUT_FILE:-${DEFAULT_INPUT}}"
OUTPUT_FILE="${OUTPUT_FILE:-${DEFAULT_OUTPUT}}"

# 检查输入文件
if [[ ! -f "$INPUT_FILE" ]]; then
    echo "错误: 输入文件不存在: $INPUT_FILE"
    exit 1
fi

TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

echo "=========================================="
echo "清理物种信息表多余空格"
echo "=========================================="
echo "输入文件: ${INPUT_FILE}"
echo "输出文件: ${OUTPUT_FILE}"
echo ""

# Step 1: 检测有多余空格的行数
space_count=$(awk -F'\t' 'NR>1 && ($2 ~ /  / || $5 ~ /  /)' "$INPUT_FILE" | wc -l)
echo "[1/2] 检测到有多余空格的行: ${space_count}"

# Step 2: 清理空格
echo "[2/2] 清理多余空格..."
{
    awk -F'\t' -v OFS='\t' 'NR==1 {
        print
        next
    }
    {
        # 清理 Species 列（第2列）中的多余空格
        if ($2 ~ /  /) {
            gsub(/  +/, " ", $2)
        }
        # 清理 Accession name 列（第5列）中的多余空格
        if ($5 ~ /  /) {
            gsub(/  +/, " ", $5)
        }
        print
    }' "$INPUT_FILE"
} >"${OUTPUT_FILE}"

# 验证清理结果
remaining=$(awk -F'\t' 'NR>1 && ($2 ~ /  / || $5 ~ /  /)' "${OUTPUT_FILE}" | wc -l)

# 统计报告
echo ""
echo "=========================================="
echo "清理完成"
echo "=========================================="
echo "总记录数: $(tail -n +2 "${OUTPUT_FILE}" | wc -l)"
echo "清理前有多余空格的行: ${space_count}"
echo "清理后仍有多余空格的行: ${remaining}"
echo "输出文件: ${OUTPUT_FILE}"
echo "=========================================="
