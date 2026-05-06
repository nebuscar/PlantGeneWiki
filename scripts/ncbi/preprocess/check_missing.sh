#!/bin/bash
# 统计并导出缺失 TaxID 和未下载的物种信息

set -euo pipefail

# 临时目录
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# 默认路径
DEFAULT_INPUT="/home/nizhu/Projects/plantsdb/data/meta/ncbi/species_list_cleaned.tsv"
DEFAULT_DOWNLOAD_DIR="/DATA/data2/downloads/genomes"
DEFAULT_OUTPUT="/home/nizhu/Projects/plantsdb/data/meta/ncbi/species_missing.tsv"

INPUT_FILE=""
DOWNLOAD_DIR=""
OUTPUT_FILE=""

# 显示帮助
show_help() {
    cat <<EOF
用法: $(basename "$0") [选项]

功能:
  统计并导出缺失 TaxID 和未下载的物种信息

选项:
  -h, --help              显示帮助信息
  -i, --input FILE        物种列表文件 (默认: ${DEFAULT_INPUT})
  -d, --download DIR      下载目录 (默认: ${DEFAULT_DOWNLOAD_DIR})
  -o, --output FILE       输出文件 (默认: ${DEFAULT_OUTPUT})

示例:
  $(basename "$0") -i species.tsv -d /downloads/genomes -o missing.tsv
  $(basename "$0")  # 使用默认路径
EOF
    exit 0
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case "$1" in
    -h | --help) show_help ;;
    -i | --input)
        INPUT_FILE="$2"
        shift 2
        ;;
    -d | --download)
        DOWNLOAD_DIR="$2"
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
DOWNLOAD_DIR="${DOWNLOAD_DIR:-${DEFAULT_DOWNLOAD_DIR}}"
OUTPUT_FILE="${OUTPUT_FILE:-${DEFAULT_OUTPUT}}"

# 检查输入文件
if [[ ! -f "$INPUT_FILE" ]]; then
    echo "错误: 输入文件不存在: $INPUT_FILE"
    exit 1
fi

echo "=========================================="
echo "统计缺失 TaxID 和未下载的物种"
echo "=========================================="
echo "物种列表: ${INPUT_FILE}"
echo "下载目录: ${DOWNLOAD_DIR}"
echo "输出文件: ${OUTPUT_FILE}"
echo ""

# Step 1: 统计缺失 TaxID 的物种
echo "[1/3] 统计缺失 TaxID 的物种..."
missing_taxid_count=$(awk -F'\t' 'NR>1 && ($3=="-" || $3=="" || $3=="NA")' "$INPUT_FILE" | wc -l)
echo "  缺失 TaxID: ${missing_taxid_count} 个"

# Step 2: 获取已下载的物种目录
echo "[2/3] 获取已下载的物种目录..."
if [[ -d "$DOWNLOAD_DIR" ]]; then
    find "${DOWNLOAD_DIR}" -maxdepth 1 -type d -exec basename {} \; 2>/dev/null | grep -v '^$' | sort -u > "${TMPDIR}/downloaded_species.txt"
    downloaded_count=$(wc -l < "${TMPDIR}/downloaded_species.txt")
    echo "  已下载: ${downloaded_count} 个"
else
    echo "  下载目录不存在，已下载: 0 个"
    > "${TMPDIR}/downloaded_species.txt"
fi

# Step 3: 导出缺失的物种信息
echo "[3/3] 导出缺失的物种信息..."

# 缺失 TaxID 的物种列表
awk -F'\t' 'NR>1 && ($3=="-" || $3=="" || $3=="NA") {print $2}' "$INPUT_FILE" | sed 's/ /_/g' | sort -u > "${TMPDIR}/missing_taxid_species.txt"

# 找出缺失 TaxID 且未下载的物种
comm -23 "${TMPDIR}/missing_taxid_species.txt" "${TMPDIR}/downloaded_species.txt" > "${TMPDIR}/missing_both.txt"

# 导出完整信息
{
    # 缺失 TaxID 且未下载
    awk -F'\t' 'NR==FNR {
        missing[$1]=1
        next
    }
    FNR>1 && ($3=="-" || $3=="" || $3=="NA") {
        name=$2
        gsub(/ /, "_", name)
        if (missing[name]) print "缺失TaxID且未下载\t" $0
    }' "${TMPDIR}/missing_both.txt" "$INPUT_FILE"

    # 缺失 TaxID 但已下载
    awk -F'\t' 'NR==FNR {
        missing[$1]=1
        next
    }
    FNR>1 && ($3=="-" || $3=="" || $3=="NA") {
        name=$2
        gsub(/ /, "_", name)
        if (!missing[name]) print "缺失TaxID已下载\t" $0
    }' "${TMPDIR}/missing_both.txt" "$INPUT_FILE"

    # 有 TaxID 但未下载
    awk -F'\t' 'NR==FNR {
        downloaded[$1]=1
        next
    }
    FNR>1 && !($3=="-" || $3=="" || $3=="NA") {
        name=$2
        gsub(/ /, "_", name)
        if (!downloaded[name]) print "有TaxID未下载\t" $0
    }' "${TMPDIR}/downloaded_species.txt" "$INPUT_FILE"
} > "${OUTPUT_FILE}"

# 统计各类别数量（排除表头）
missing_taxid_not_downloaded=$(awk -F'\t' '$1=="缺失TaxID且未下载"' "${OUTPUT_FILE}" | wc -l)
missing_taxid_downloaded=$(awk -F'\t' '$1=="缺失TaxID已下载"' "${OUTPUT_FILE}" | wc -l)
has_taxid_not_downloaded=$(awk -F'\t' '$1=="有TaxID未下载"' "${OUTPUT_FILE}" | wc -l)

echo ""
echo "=========================================="
echo "统计报告"
echo "=========================================="
echo "物种列表总数: $(tail -n +2 "$INPUT_FILE" | wc -l)"
echo ""
echo "缺失 TaxID 且未下载: ${missing_taxid_not_downloaded} 个"
echo "缺失 TaxID 但已下载: ${missing_taxid_downloaded} 个"
echo "有 TaxID 但未下载: ${has_taxid_not_downloaded} 个"
echo ""
echo "输出文件: ${OUTPUT_FILE}"
echo "=========================================="

# 临时文件由 trap 自动清理