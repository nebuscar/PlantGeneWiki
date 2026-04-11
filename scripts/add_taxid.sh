#!/bin/bash
# 使用 Taxonkit 为物种列表添加 Taxonomy ID
# 读取第二列(Species)，查询 TaxID，保持原顺序与重复行

show_help() {
    cat <<EOF
用法: $0 [选项]
功能: 批量为物种列表添加 TaxID，自动去重查询，保持原顺序

必需参数:
  -i, --input FILE     输入物种列表文件 (tab分隔，第2列为物种拉丁名)
  -o, --output FILE    输出文件 (自动添加TaxID列)

可选参数:
  -h, --help           显示帮助信息

示例:
  $0 -i data/meta/species_list.txt -o data/meta/species_list_with_taxid.txt
EOF
}

INPUT=""
OUTPUT=""

while [[ $# -gt 0 ]]; do
    case "$1" in
    -i | --input)
        INPUT="$2"
        shift 2
        ;;
    -o | --output)
        OUTPUT="$2"
        shift 2
        ;;
    -h | --help)
        show_help
        exit 0
        ;;
    *)
        echo "错误：未知参数 $1"
        show_help
        exit 1
        ;;
    esac
done

if [[ -z "$INPUT" || -z "$OUTPUT" ]]; then
    echo "错误：必须指定 -i 输入文件和 -o 输出文件"
    echo
    show_help
    exit 1
fi

if [[ ! -f "$INPUT" ]]; then
    echo "错误：输入文件不存在：$INPUT"
    exit 1
fi

echo "开始查询 Taxonomy ID..."
echo "输入文件: $INPUT"
echo "输出文件: $OUTPUT"

temp_taxid_map=$(mktemp)
temp_failed=$(mktemp)

unique_species=$(tail -n +2 "${INPUT}" | cut -f2 | sort -u)

echo "$unique_species" | taxonkit name2taxid -s --show-rank >"${temp_taxid_map}" 2>/dev/null

declare -A taxid_map
while IFS=$'\t' read -r name taxid rank; do
    if [[ -n "$taxid" && "$taxid" != "0" ]]; then
        taxid_map["$name"]="$taxid"
    fi
done <"${temp_taxid_map}"

{
    head -n 1 "${INPUT}" | awk -F '\t' '{print $1"\t"$2"\tTaxonomy ID\t"$3"\t"$4"\t"$5"\t"$6"\t"$7}'

    tail -n +2 "${INPUT}" | while IFS=$'\t' read -r no species ploidy accession order family clade; do
        taxid="${taxid_map[$species]}"
        if [[ -z "$taxid" ]]; then
            echo "$species" >>"${temp_failed}"
            taxid="-"
        fi
        echo -e "${no}\t${species}\t${taxid}\t${ploidy}\t${accession}\t${order}\t${family}\t${clade}"
    done
} >"${OUTPUT}"

total=$(tail -n +2 "${INPUT}" | wc -l)
found=$(grep -cv '^$' "${temp_taxid_map}")
failed=$(wc -l <"${temp_failed}")

echo ""
echo "=========================================="
echo "完成!"
echo "总行数: ${total}"
echo "成功获取 TaxID: ${found}"
echo "未找到 TaxID: ${failed}"
echo "输出文件: ${OUTPUT}"
echo "=========================================="

if [[ -s "${temp_failed}" ]]; then
    echo ""
    echo "未找到 Taxonomy ID 的物种:"
    cat "${temp_failed}" | sort -u | head -20
fi

rm -f "${temp_taxid_map}" "${temp_failed}"

echo ""
echo "✅ 全部完成！"
