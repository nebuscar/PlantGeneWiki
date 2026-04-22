#!/bin/bash
set -euo pipefail

# ==============================================================================
# 植物标准基因组库 - 物种列表去重脚本
# 功能：按物种名(Species)去重，每个物种仅保留第一条记录
# 适用表格：No.species	Species	Taxonomy ID	Ploidy	Accession name	Order	Family	Clade
# ==============================================================================

show_help() {
    cat <<EOF
用法:
  $0 -i 输入文件 -o 输出文件 [选项]

功能:
  1. 严格按照【第二列 物种名】去重
  2. 每个物种只保留【第一次出现】的记录
  3. 表头完整保留，不乱序、不丢失
  4. 适合构建基因组数据库、同源比对分析

必选参数:
  -i, --input     原始物种列表文件 (必填)
  -o, --output    输出去重后的标准库文件 (必填)

可选参数:
  -s, --stat      显示去重统计信息
  -h, --help      显示帮助信息

示例:
  $0 -i species_list.txt -o species_list_unique.txt
  $0 -i list.txt -o unique_list.txt -s
EOF
    exit 0
}

# 默认参数
INPUT=""
OUTPUT=""
SHOW_STAT="no"

# 解析参数
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
    -s | --stat)
        SHOW_STAT="yes"
        shift
        ;;
    -h | --help)
        show_help
        ;;
    *)
        echo -e "\n错误：未知参数 $1\n"
        show_help
        ;;
    esac
done

# 检查必填参数
if [[ -z "$INPUT" || -z "$OUTPUT" ]]; then
    echo -e "\n错误：必须指定 -i/--input 和 -o/--output\n"
    show_help
fi

if [[ ! -f "$INPUT" ]]; then
    echo -e "\n错误：输入文件不存在：$INPUT\n"
    exit 1
fi

# ==============================================================================
# 核心去重逻辑：强制 TAB 分割，确保物种名不会因空格错位
# ==============================================================================
echo -e "\n============================================="
echo " 开始去重物种清单..."
echo " 输入文件：$INPUT"
echo " 输出文件：$OUTPUT"
echo -e "=============================================\n"

awk '
BEGIN {
    FS = "\t";
    OFS = "\t";
}
NR == 1 {
    print;
    next;
}
{
    species = $2;
    if (!seen[species]++) {
        print;
    }
}
' "$INPUT" >"$OUTPUT"

# ==============================================================================
# 统计信息
# ==============================================================================
if [[ "$SHOW_STAT" == "yes" ]]; then
    raw_total=$(awk 'NR>1' "$INPUT" | wc -l)
    unique_total=$(awk 'NR>1' "$OUTPUT" | wc -l)
    removed=$((raw_total - unique_total))

    echo -e "\n============================================="
    echo " 去重统计结果"
    echo "============================================="
    echo " 原始总行数：$raw_total"
    echo " 去重后物种数：$unique_total"
    echo " 移除冗余条目：$removed"
    echo -e "=============================================\n"
fi

echo -e "✅ 去重完成！每个物种仅保留一条记录。\n"
