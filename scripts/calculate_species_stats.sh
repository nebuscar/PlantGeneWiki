#!/bin/bash
set -euo pipefail

# ==============================================================================
# 物种数量统计脚本
# 功能：按 目(Order) / 科(Family) / 属(Genus/Clade) 统计唯一物种数量
# 输出：干净 TXT 表格，带表头
# ==============================================================================

show_help() {
    cat <<EOF
用法:
  $0 -i 输入物种表 -o 输出统计文件 -g 分组类型

功能:
  对物种列表自动去重，然后按指定分组统计物种数量
  输出标准 TXT 表格，可直接用于论文、报告、建库

必选参数:
  -i, --input     输入物种列表文件 (TSV格式，必填)
  -o, --output    输出统计结果文件 (txt/tsv，必填)
  -g, --group     分组类型，可选：order / family / genus (必填)

可选参数:
  -h, --help      显示帮助信息

示例:
  $0 -i species_list.txt -o stats_order.txt -g order
  $0 -i species_list.txt -o stats_family.txt -g family
  $0 -i species_list.txt -o stats_genus.txt -g genus
EOF
    exit 0
}

# 参数初始化
INPUT=""
OUTPUT=""
GROUP=""

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
    -g | --group)
        GROUP="$2"
        shift 2
        ;;
    -h | --help) show_help ;;
    *)
        echo "错误参数：$1"
        show_help
        ;;
    esac
done

# 参数检查
if [[ -z "$INPUT" || -z "$OUTPUT" || -z "$GROUP" ]]; then
    echo "错误：-i -o -g 均为必填参数"
    show_help
fi

if [[ ! -f "$INPUT" ]]; then
    echo "错误：输入文件不存在：$INPUT"
    exit 1
fi

# 确定分组对应的列 & 输出表头
case "$GROUP" in
order | Order)
    COL=6
    HEADER="Order\tSpecies_Count"
    ;;
family | Family)
    COL=7
    HEADER="Family\tSpecies_Count"
    ;;
genus | Genus)
    COL=8
    HEADER="Genus\tSpecies_Count"
    ;;
*)
    echo "分组必须是 order / family / genus"
    exit 1
    ;;
esac

echo "============================================="
echo " 开始统计..."
echo " 输入文件：$INPUT"
echo " 输出文件：$OUTPUT"
echo " 分组类型：$GROUP (第 $COL 列)"
echo -e "=============================================\n"

# ==============================================================================
# 核心统计逻辑
# 1. 跳过表头
# 2. 按物种名去重
# 3. 按分组列统计数量
# 4. 按数量降序输出
# ==============================================================================
awk 'BEGIN {
    FS = "\t";
    OFS = "\t";
}
NR == 1 { next }
{
    species = $2;
    group = $'$COL';
    if (!seen_species[species]++) {
        groups[group]++;
    }
}
END {
    print "'"$HEADER"'";
    for (g in groups) {
        print g, groups[g];
    }
}' "$INPUT" | sort -k2,2nr >"$OUTPUT"

echo -e "✅ 统计完成！输出文件：$OUTPUT\n"
echo "预览（前10行）："
head -n 10 "$OUTPUT"
