#!/bin/bash
# NCBI 基因组批量下载脚本

project_dir="/home/nizhu/Projects/plantsdb"
meta_dir="${project_dir}/data/meta/species_list_with_taxid.txt"
# out_dir="${project_dir}/downloads/genomes"
out_dir="/data/data2/downloads/genomes"
log_dir="${project_dir}/downloads/logs"
include_types="genome,protein,gff3,gbff"

show_help() {
    echo "用法: $0 [模式] [选项] [筛选名称/文件 ...]"
    echo ""
    echo "模式:"
    echo "  order   按目 (Order) 分批下载"
    echo "  family  按科 (Family) 分批下载"
    echo "  genus   按属 (Genus) 分批下载 (默认)"
    echo "  all     下载全部物种"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示帮助信息"
    echo "  -l, --list     列出所有可用的批次"
    echo "  -t, --test     测试模式，只下载单个物种"
    echo ""
    echo "筛选参数 (支持多个，自动判断是名称还是文件):"
    echo "  <名称>         按当前模式筛选（属名/科名/目名）"
    echo "  <文件>         从文件读取筛选名称列表（每行一个）"
    echo "  无筛选参数     下载当前模式下全部"
    echo ""
    echo "示例:"
    echo "  $0 -l family                       # 查看可用的科列表"
    echo "  $0 order Brassicales              # 下载 Brassicales 目"
    echo "  $0 family Fabaceae                # 只下载 Fabaceae 科"
    echo "  $0 genus Oryza                    # 下载 Oryza 属"
    echo "  $0 genus Acer Arbus               # 下载 Acer 和 Arbus 两个属"
    echo "  $0 genus species_list.txt         # 从文件读取属名列表"
    echo "  $0 order orders.txt               # 从文件读取目名列表"
    echo "  $0 all                            # 下载全部物种"
    echo "  $0 -t \"Arabidopsis thaliana\"   # 测试下载单个物种"
    echo ""
    exit 0
}

show_list() {
    local col
    case "$1" in
    order) col=6 ;;
    family) col=7 ;;
    genus) col=8 ;;
    *)
        col=8

        ;;
    esac
    awk -F'\t' -v col="$col" 'NR>1 {print $col}' "${meta_dir}" | sort | uniq -c | sort -rn
    exit 0
}

download_species() {
    local species="$1"
    local taxid="$2"
    local species_name=$(echo "$species" | tr ' ' '_')
    local species_dir="${out_dir}/${species_name}"
    local zip_file="${species_dir}.zip"

    # 跳过无 TaxID 的物种
    if [ -z "$taxid" ] || [ "$taxid" = "-" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${species} | ${taxid:-NA} | 跳过 | 无TaxID" | tee -a "$SKIP_LOG" "$TOTAL_LOG"
        return 0
    fi

    # 检查是否已下载（解压后文件或未解压的 zip 均视为已下载）
    if [ -f "${species_dir}/${species_name}_genome.fna" ] ||
        [ -f "${species_dir}/${species_name}_protein.faa" ] ||
        [ -f "${species_dir}/${species_name}_annotation.gff" ] ||
        [ -f "${species_dir}/${species_name}_annotation.gbff" ] ||
        [ -f "${zip_file}" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${species} | ${taxid} | 跳过 | 已存在" | tee -a "$SKIP_LOG" "$TOTAL_LOG"
        return 0
    fi
    echo ""
    echo "============================="
    echo "下载: ${species} (TaxID: ${taxid})"
    echo "输出路径：$zip_file"
    echo "============================="
    echo ""
    mkdir -p "$species_dir"
    datasets download genome taxon "$taxid" \
        --include $include_types \
        --filename "${zip_file}" 2>&1 | grep -v "New version"

    sleep 1

    if [ ! -f "$zip_file" ] || [ ! -s "$zip_file" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${species} | ${taxid} | 失败 | NCBI未找到" | tee -a "$FAIL_LOG" "$TOTAL_LOG"
        return 1
    fi

    if unzip -t $zip_file; then
        echo "解压: $species (TaxID: $taxid)"
        unzip -o "$zip_file" -d "$species_dir" >/dev/null 2>&1
        # unzip -o "$zip_file" -d "$species_dir"
        rm -f "$zip_file"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${species} | ${taxid} | 失败 | ZIP文件无效" | tee -a "$FAIL_LOG" "$TOTAL_LOG"
        return 1
    fi

    # 整理文件：比较所有 accession，选择收录最完整的
    (
        cd "$species_dir"
        find . -name "*.gz" -exec gunzip -f {} \; 2>/dev/null || true

        best_dir=""
        best_score=0

        # 遍历所有 accession 目录，计算完整性得分（RefSeq 优先：先 GCA 后 GCF，分数相同时 GCF 覆盖）
        for dir in ncbi_dataset/data/GCA_* ncbi_dataset/data/GCF_*; do
            [ -d "$dir" ] || continue
            score=0
            [ -n "$(ls "$dir"/*.fna 2>/dev/null)" ] && ((score += 1))
            [ -n "$(ls "$dir"/*.faa 2>/dev/null)" ] && ((score += 1))
            [ -n "$(ls "$dir"/*.gff 2>/dev/null)" ] && ((score += 2))
            [ -n "$(ls "$dir"/*.gbff 2>/dev/null)" ] && ((score += 1))

            if [ "$score" -gt "$best_score" ]; then
                best_score=$score
                best_dir="$dir"
            fi
        done

        # 复制最完整的文件
        if [ -n "$best_dir" ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${species} | ${taxid} | 选择组装版本: $best_dir" | tee -a "$TOTAL_LOG"
            cp "$best_dir"/*.fna . 2>/dev/null || true
            cp "$best_dir"/*.faa . 2>/dev/null || true
            cp "$best_dir"/*.gff . 2>/dev/null || true
            cp "$best_dir"/*.gbff . 2>/dev/null || true
        fi

        # 重命名
        [ -f "${species_name}_genome.fna" ] || mv *.fna "${species_name}_genome.fna" 2>/dev/null || true
        [ -f "${species_name}_annotation.gff" ] || mv *.gff "${species_name}_annotation.gff" 2>/dev/null || true
        [ -f "${species_name}_protein.faa" ] || mv *.faa "${species_name}_protein.faa" 2>/dev/null || true
        [ -f "${species_name}_annotation.gbff" ] || mv *.gbff "${species_name}_annotation.gbff" 2>/dev/null || true
    )

    if [ -f "${species_dir}/${species_name}_genome.fna" ] &&
        [ -f "${species_dir}/${species_name}_protein.faa" ] &&
        { [ -f "${species_dir}/${species_name}_annotation.gff" ] ||
            [ -f "${species_dir}/${species_name}_annotation.gbff" ]; }; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${species} | ${taxid} | 成功 | 文件完整" | tee -a "$SUCCESS_LOG" "$TOTAL_LOG"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${species} | ${taxid} | 失败 | 文件不完整" | tee -a "$FAIL_LOG" "$TOTAL_LOG"
    fi
}

# 解析参数
BATCH_MODE="genus"
BATCH_FILTERS=()
TEST_MODE="no"

while [[ $# -gt 0 ]]; do
    case "$1" in
    -h | --help) show_help ;;
    -l | --list)
        show_list "${2:-genus}"
        shift
        ;;
    -t | --test)
        TEST_MODE="yes"
        TEST_SPECIES="$2"
        shift
        ;;
    order | family | genus | all)
        BATCH_MODE="$1"
        ;;
    -*)
        echo "未知选项: $1" >&2
        show_help
        ;;
    *)
        # 收集所有非选项参数作为筛选名称/文件
        BATCH_FILTERS+=("$1")
        ;;
    esac
    shift
done

mkdir -p $out_dir $log_dir

# 日志文件
SUCCESS_LOG="${log_dir}/success.log"
FAIL_LOG="${log_dir}/fail.log"
SKIP_LOG="${log_dir}/skip.log"
TOTAL_LOG="${log_dir}/total.log"

# 清空日志
: >"$SUCCESS_LOG"
: >"$FAIL_LOG"
: >"$SKIP_LOG"
: >"$TOTAL_LOG"

if [ ! -f "${meta_dir}" ]; then
    echo "错误: 未找到物种列表文件 ${meta_dir}" | tee -a $TOTAL_LOG
    exit 1
fi

# 测试模式
if [ "$TEST_MODE" = "yes" ] && [ -n "$TEST_SPECIES" ]; then
    line=$(awk -F'\t' -v name="$TEST_SPECIES" '$2==name {print $2"\t"$3; exit}' "${meta_dir}")
    species=$(echo "$line" | cut -f1)
    taxid=$(echo "$line" | cut -f2)
    download_species "$species" "$taxid"
    exit 0
fi

# 展开筛选参数：自动判断是文件还是名称
expand_filters() {
    local mode_label="$1"
    shift
    expanded=()
    for item in "$@"; do
        if [ -f "$item" ]; then
            echo "从文件读取${mode_label}列表: $item"
            while IFS= read -r line || [[ -n "$line" ]]; do
                [[ -z "$line" || "$line" =~ ^# ]] && continue
                expanded+=("$(echo "$line" | xargs)")
            done < "$item"
        else
            expanded+=("$item")
        fi
    done
}

# 批量下载
case "$BATCH_MODE" in
order | family | genus)
    col=$(case "$BATCH_MODE" in order) echo 6 ;; family) echo 7 ;; genus) echo 8 ;; esac)
    mode_label=$(case "$BATCH_MODE" in order) echo "目名" ;; family) echo "科名" ;; genus) echo "属名" ;; esac)
    awk -F'\t' -v col="$col" 'NR>1 {print $col}' "${meta_dir}" | sort -u >/tmp/groups.txt

    if [ ${#BATCH_FILTERS[@]} -gt 0 ]; then
        expand_filters "$mode_label" "${BATCH_FILTERS[@]}"
        groups=""
        for filter in "${expanded[@]}"; do
            matched=$(grep -i "^${filter}$" /tmp/groups.txt)
            if [ -n "$matched" ]; then
                groups="${groups}${matched}\n"
            else
                echo "警告: 未找到${mode_label} '$filter'"
            fi
        done
        groups=$(echo -e "$groups" | sort -u | grep -v '^$')
    else
        groups=$(cat /tmp/groups.txt)
    fi

    for group in $groups; do
        echo "========== 批次: $group =========="
        awk -F'\t' -v g="$group" -v col="$col" '$col==g {print $2"\t"$3}' "${meta_dir}" |
            while IFS=$'\t' read -r species taxid; do
                download_species "$species" "$taxid"
            done
    done
    rm -f /tmp/groups.txt
    ;;
all | "")
    awk -F'\t' 'NR>1 {print $2"\t"$3}' "${meta_dir}" | sort -u |
        while IFS=$'\t' read -r species taxid; do
            download_species "$species" "$taxid"
        done
    ;;
esac

# 统计结果
success_count=$(wc -l <"$SUCCESS_LOG" 2>/dev/null || echo 0)
fail_count=$(wc -l <"$FAIL_LOG" 2>/dev/null || echo 0)
skip_count=$(wc -l <"$SKIP_LOG" 2>/dev/null || echo 0)

echo ""
echo "=========================================="
echo "下载完成!"
echo "成功: ${success_count} 个物种"
echo "失败: ${fail_count} 个物种"
echo "跳过: ${skip_count} 个物种"
echo "=========================================="
echo ""
echo "日志文件:"
echo "  总日志: ${TOTAL_LOG}"
echo "  成功: ${SUCCESS_LOG}"
echo "  失败: ${FAIL_LOG}"
echo "  跳过: ${SKIP_LOG}"
