#!/bin/bash
# 使用 Taxonkit 为 species_list.txt 添加 Taxonomy ID
# 读取第二列(Species)，查询 Taxonomy ID，添加到第三列
# 保持重复行，保留原顺序

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SPECIES_LIST="${PROJECT_ROOT}/data/meta/species_list.txt"
OUTPUT_FILE="${PROJECT_ROOT}/data/meta/species_list_with_taxid.txt"

echo "开始查询 Taxonomy ID..."

# 临时文件
temp_taxid_map=$(mktemp)
temp_failed=$(mktemp)

# 提取唯一物种名进行查询（避免重复查询）
unique_species=$(tail -n +2 "${SPECIES_LIST}" | cut -f2 | sort -u)

# 使用 taxonkit 批量查询唯一物种
echo "$unique_species" | taxonkit name2taxid -s --show-rank >"${temp_taxid_map}" 2>/dev/null

# 创建 taxid 查找表（只保留成功的）
declare -A taxid_map
while IFS=$'\t' read -r name taxid rank; do
    if [ -n "$taxid" ]; then
        taxid_map["$name"]="$taxid"
    fi
done <"${temp_taxid_map}"

# 读取原始文件，处理每一行
{
    # 输出表头：添加 Taxonomy ID 列（在 Species 后）
    head -n 1 "${SPECIES_LIST}" | awk -F'\t' '{print $1"\t"$2"\tTaxonomy ID\t"$3"\t"$4"\t"$5"\t"$6"\t"$7}'

    # 处理数据行：在 Species 后插入 Taxonomy ID，保持重复行
    tail -n +2 "${SPECIES_LIST}" | while IFS=$'\t' read -r no species ploidy accession order family clade; do
        taxid="${taxid_map[$species]}"

        if [ -z "$taxid" ]; then
            echo "$species" >>"${temp_failed}"
            taxid="-"
        fi

        echo -e "${no}\t${species}\t${taxid}\t${ploidy}\t${accession}\t${order}\t${family}\t${clade}"
    done
} >"${OUTPUT_FILE}"

# 统计结果
total=$(tail -n +2 "${SPECIES_LIST}" | wc -l)
found=$(grep -v "^$" "${temp_taxid_map}" | wc -l)
failed=$(wc -l <"${temp_failed}")

echo ""
echo "=========================================="
echo "完成!"
echo "总行数: ${total}"
echo "成功获取 TaxID: ${found}"
echo "未找到 TaxID: ${failed}"
echo "输出文件: ${OUTPUT_FILE}"
echo "=========================================="

if [ -s "${temp_failed}" ]; then
    echo ""
    echo "未找到 Taxonomy ID 的物种:"
    cat "${temp_failed}" | sort -u | head -20
fi

# 清理临时文件
rm -f "${temp_taxid_map}" "${temp_failed}"
