#!/bin/bash
#============================================================================
# 物种分类筛选脚本
# 功能：基于物种信息表进行分类统计和筛选
# 作者：自动化脚本
#============================================================================

set -e

# 默认值
RANK=""                    # 筛选级别：order, family, genus
NAME=""                    # 自定义筛选类别名称
COUNT_MODE=false           # 按分类级别统计物种数量
COUNT_VALUE=""             # 精确匹配物种数量
COUNT_MIN=""               # 最小物种数量
COUNT_MAX=""               # 最大物种数量
INPUT_FILE="/home/nizhu/zhenwen/species_list_with_taxid.txt"
OUTPUT_FILE=""             # 输出文件路径
OUTPUT_FORMAT="xlsx"       # 默认输出格式

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 帮助信息
usage() {
    cat << EOF
${GREEN}物种分类筛选脚本${NC}
用法: $0 [选项]

${YELLOW}选项:${NC}
    -r, --rank <级别>          指定筛选级别：order(目), family(科), genus(属)
    -n, --name <名称>          自定义筛选类别具体名称 (例如: Fabales, Fabaceae, Acer)
    -c, --count                按分类级别统计物种数量
    -v, --count-value <数量>   筛选物种数量等于指定值的类别
    -m, --min <数量>           筛选物种数量最小值 (需配合 --max 使用)
    -M, --max <数量>           筛选物种数量最大值 (需配合 --min 使用)
    -i, --input <文件>         输入文件路径 (默认: /home/nizhu/zhenwen/species_list_with_taxid.txt)
    -o, --output <文件>        输出文件路径 (不含扩展名)
    -f, --format <格式>        输出格式：txt, csv, tsv, xlsx (默认: xlsx)
    -h, --help                 显示此帮助信息

${YELLOW}示例:${NC}
    # 统计各目的物种数量
    $0 -c -r order -o order_stats

    # 筛选Fabales目的所有物种
    $0 -r order -n Fabales -o fabales_species

    # 筛选物种数量为5的科
    $0 -c -r family -v 5 -o family_5species

    # 筛选物种数量在10-50之间的属
    $0 -c -r genus -m 10 -M 50 -o genus_10_50

    # 筛选Fabaceae科并导出为CSV
    $0 -r family -n Fabaceae -f csv -o fabaceae

EOF
    exit 1
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--rank)
            RANK="$2"
            if [[ ! "$RANK" =~ ^(order|family|genus)$ ]]; then
                echo -e "${RED}错误: --rank 必须是 order, family 或 genus${NC}" >&2
                exit 1
            fi
            shift 2
            ;;
        -n|--name)
            NAME="$2"
            shift 2
            ;;
        -c|--count)
            COUNT_MODE=true
            shift
            ;;
        -v|--count-value)
            COUNT_VALUE="$2"
            if ! [[ "$COUNT_VALUE" =~ ^[0-9]+$ ]]; then
                echo -e "${RED}错误: --count-value 必须是数字${NC}" >&2
                exit 1
            fi
            shift 2
            ;;
        -m|--min)
            COUNT_MIN="$2"
            if ! [[ "$COUNT_MIN" =~ ^[0-9]+$ ]]; then
                echo -e "${RED}错误: --min 必须是数字${NC}" >&2
                exit 1
            fi
            shift 2
            ;;
        -M|--max)
            COUNT_MAX="$2"
            if ! [[ "$COUNT_MAX" =~ ^[0-9]+$ ]]; then
                echo -e "${RED}错误: --max 必须是数字${NC}" >&2
                exit 1
            fi
            shift 2
            ;;
        -i|--input)
            INPUT_FILE="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -f|--format)
            OUTPUT_FORMAT="$2"
            if [[ ! "$OUTPUT_FORMAT" =~ ^(txt|csv|tsv|xlsx)$ ]]; then
                echo -e "${RED}错误: --format 必须是 txt, csv, tsv 或 xlsx${NC}" >&2
                exit 1
            fi
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo -e "${RED}错误: 未知选项 $1${NC}" >&2
            usage
            ;;
    esac
done

# 验证输入文件
if [[ ! -f "$INPUT_FILE" ]]; then
    echo -e "${RED}错误: 输入文件不存在: $INPUT_FILE${NC}" >&2
    exit 1
fi

# 检查必要的列
check_columns() {
    local col=$1
    local header=$(head -1 "$INPUT_FILE" | tr '\t' '\n' | cat -n | grep -w "$col" | awk '{print $1}')
    if [[ -z "$header" ]]; then
        echo -e "${RED}错误: 找不到列: $col${NC}" >&2
        exit 1
    fi
}

# 根据级别获取列名
get_column_name() {
    case "$RANK" in
        order)  echo "Order" ;;
        family) echo "Family" ;;
        genus)  echo "Clade" ;;
    esac
}

# 生成临时工作文件
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# 解析列位置
HEADER_LINE=$(head -1 "$INPUT_FILE")
COL_NO=$(echo "$HEADER_LINE" | tr '\t' '\n' | cat -n | grep -w "$(get_column_name)" | awk '{print $1}')

# 构建筛选条件
FILTER_SQL=""
if [[ -n "$NAME" ]]; then
    FILTER_SQL="${FILTER_SQL} WHERE ${RANK} = '${NAME}'"
fi

# 统计模式
if [[ "$COUNT_MODE" == true ]]; then
    echo -e "${GREEN}执行统计模式...${NC}"
    
    # 生成统计结果
    if [[ -n "$OUTPUT_FILE" ]]; then
        TEMP_STATS="$TEMP_DIR/stats.tsv"
    else
        TEMP_STATS="/dev/stdout"
    fi
    
    # 统计每个类别的物种数量（去重）
    awk -F'\t' -v col="$COL_NO" '
    BEGIN { OFS="\t" }
    NR > 1 && $col != "" && $col != "-" {
        count[$col]++
        species[$col,$count[$col]] = $2
    }
    END {
        n = asorti(count, sorted)
        for (i = 1; i <= n; i++) {
            rank_name = sorted[i]
            species_count = count[rank_name]
            print rank_name, species_count
        }
    }
    ' "$INPUT_FILE" | sort > "$TEMP_STATS"
    
    # 应用数量筛选条件
    if [[ -n "$COUNT_VALUE" ]]; then
        TEMP_FILTERED="$TEMP_DIR/filtered.tsv"
        grep "$(printf '\t%d$' "$COUNT_VALUE")" "$TEMP_STATS" > "$TEMP_FILTERED" || true
        mv "$TEMP_FILTERED" "$TEMP_STATS"
    fi
    
    if [[ -n "$COUNT_MIN" ]] && [[ -n "$COUNT_MAX" ]]; then
        TEMP_FILTERED="$TEMP_DIR/filtered.tsv"
        awk -v min="$COUNT_MIN" -v max="$COUNT_MAX" -F'\t' '$2 >= min && $2 <= max' "$TEMP_STATS" > "$TEMP_FILTERED"
        mv "$TEMP_FILTERED" "$TEMP_STATS"
    elif [[ -n "$COUNT_MIN" ]]; then
        TEMP_FILTERED="$TEMP_DIR/filtered.tsv"
        awk -v min="$COUNT_MIN" -F'\t' '$2 >= min' "$TEMP_STATS" > "$TEMP_FILTERED"
        mv "$TEMP_FILTERED" "$TEMP_STATS"
    elif [[ -n "$COUNT_MAX" ]]; then
        TEMP_FILTERED="$TEMP_DIR/filtered.tsv"
        awk -v max="$COUNT_MAX" -F'\t' '$2 <= max' "$TEMP_STATS" > "$TEMP_FILTERED"
        mv "$TEMP_FILTERED" "$TEMP_STATS"
    fi
    
    # 输出结果
    if [[ -n "$OUTPUT_FILE" ]]; then
        case "$OUTPUT_FORMAT" in
            xlsx)
                python3 << PYTHON_SCRIPT
import pandas as pd
import sys

df = pd.read_csv("$TEMP_STATS", sep='\t', header=None, names=['$RANK', 'Species Count'])
output_file = "${OUTPUT_FILE}.xlsx"
df.to_excel(output_file, index=False, engine='openpyxl')
print(f"结果已保存到: {output_file}")
PYTHON_SCRIPT
                ;;
            csv)
                sed 's/\t/,/g' "$TEMP_STATS" > "${OUTPUT_FILE}.csv"
                echo -e "${GREEN}结果已保存到: ${OUTPUT_FILE}.csv${NC}"
                ;;
            tsv)
                cp "$TEMP_STATS" "${OUTPUT_FILE}.tsv"
                echo -e "${GREEN}结果已保存到: ${OUTPUT_FILE}.tsv${NC}"
                ;;
            txt)
                cp "$TEMP_STATS" "${OUTPUT_FILE}.txt"
                echo -e "${GREEN}结果已保存到: ${OUTPUT_FILE}.txt${NC}"
                ;;
        esac
    else
        cat "$TEMP_STATS"
    fi
    
# 筛选具体类别模式
elif [[ -n "$RANK" ]] && [[ -n "$NAME" ]]; then
    echo -e "${GREEN}筛选 $RANK: $NAME${NC}"
    
    TEMP_RESULT="$TEMP_DIR/result.tsv"
    
    awk -F'\t' -v col="$COL_NO" -v target="$NAME" '
    BEGIN { OFS="\t"; print "No", "Species", "Taxonomy ID", "Ploidy", "Accession name", "Order", "Family", "Clade" }
    NR > 1 && $col == target {
        print $1, $2, $3, $4, $5, $6, $7, $8
    }
    ' "$INPUT_FILE" > "$TEMP_RESULT"
    
    if [[ -n "$OUTPUT_FILE" ]]; then
        case "$OUTPUT_FORMAT" in
            xlsx)
                python3 << PYTHON_SCRIPT
import pandas as pd
import sys

# 读取TSV并处理可能的混合分隔符问题
with open("$TEMP_RESULT", 'r') as f:
    lines = f.readlines()

data = []
for line in lines:
    fields = line.strip().split('\t')
    if len(fields) >= 8:
        data.append(fields[:8])
    elif len(fields) > 1:
        while len(fields) < 8:
            fields.append('')
        data.append(fields)

df = pd.DataFrame(data[1:], columns=data[0])
output_file = "${OUTPUT_FILE}.xlsx"
df.to_excel(output_file, index=False, engine='openpyxl')
print(f"结果已保存到: {output_file}")
PYTHON_SCRIPT
                ;;
            csv)
                sed 's/\t/,/g' "$TEMP_RESULT" > "${OUTPUT_FILE}.csv"
                echo -e "${GREEN}结果已保存到: ${OUTPUT_FILE}.csv${NC}"
                ;;
            tsv)
                cp "$TEMP_RESULT" "${OUTPUT_FILE}.tsv"
                echo -e "${GREEN}结果已保存到: ${OUTPUT_FILE}.tsv${NC}"
                ;;
            txt)
                cp "$TEMP_RESULT" "${OUTPUT_FILE}.txt"
                echo -e "${GREEN}结果已保存到: ${OUTPUT_FILE}.txt${NC}"
                ;;
        esac
    else
        cat "$TEMP_RESULT"
    fi
    
# 列出可用类别
elif [[ -n "$RANK" ]]; then
    echo -e "${GREEN}列出所有 $RANK 类别:${NC}"
    awk -F'\t' -v col="$COL_NO" '
    NR > 1 && $col != "" && $col != "-" {
        if (!seen[$col]++) {
            print $col
        }
    }
    ' "$INPUT_FILE" | sort
    
else
    echo -e "${RED}错误: 请指定操作模式${NC}" >&2
    echo "  - 使用 -c 进行统计模式" >&2
    echo "  - 使用 -r 和 -n 进行筛选模式" >&2
    exit 1
fi

echo -e "${GREEN}完成!${NC}"
