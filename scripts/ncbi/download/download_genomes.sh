#!/bin/bash
# NCBI 基因组批量下载脚本

project_dir="/home/nizhu/Projects/plantsdb"
default_input_dir="${project_dir}/data/meta/ncbi/species_list_with_taxid.txt"
input_dir="${default_input_dir}"
default_out_dir="/DATA/data2/downloads/genomes"
out_dir="${default_out_dir}"
default_log_dir="${project_dir}/downloads/logs"
log_dir="${default_log_dir}"

# 默认参数
include_types="genome,protein,cds,gff3,gbff"
assembly_level="chromosome,complete"
assembly_source="all"
assembly_version="latest"
annotated="no"
reference="no"
exclude_atypical="yes"
exclude_multi_isolate="yes"
mag="all"
released_after=""
released_before=""

show_help() {
    cat <<EOF
用法: $0 [模式] [选项] [筛选名称/文件 ...]

模式:
  order   按目 (Order) 分批下载
  family  按科 (Family) 分批下载
  genus   按属 (Genus) 分批下载 (默认)
  all     下载全部物种

选项:
  -h, --help              显示帮助信息
  -l, --list              列出所有可用的批次
  -t, --test              测试模式，只下载单个物种
  -i, --input FILE        指定物种列表文件 (默认: ${default_input_dir})
  -o, --outdir DIR        指定下载保存目录 (默认: ${default_out_dir})
  -logdir, --logdir DIR   指定日志保存目录 (默认: ${default_log_dir})

NCBI datasets 参数:
  --include <types>       下载的数据文件类型 (逗号分隔)
                          可选: genome,rna,protein,cds,gff3,gtf,gbff,seq-report,all,none
                          (默认: genome,protein,cds,gff3,gbff)
  --assembly-level <lvls> 限制组装级别 (逗号分隔)
                          可选: chromosome,complete,contig,scaffold
                          (默认: chromosome,complete)
  --assembly-source <src> 限制组装来源: RefSeq 或 GenBank (默认: all)
  --assembly-version <v>  限制组装版本: latest 或 all (默认: latest)
  --annotated             限制为有注释的基因组 (默认: 不限制)
  --reference             限制为参考基因组 (默认: 不限制)
  --exclude-atypical      排除非典型组装 (默认: 排除)
  --exclude-multi-isolate 排除多分离株项目的组装 (默认: 排除)
  --mag <val>             限制 MAG 组装: only 或 exclude (默认: all)
  --released-after <date> 限制在此日期之后发布的基因组 (默认: 不限制)
  --released-before <date>限制在此日期之前发布的基因组 (默认: 不限制)

筛选参数 (支持多个，自动判断是名称还是文件):
  <名称>         按当前模式筛选（属名/科名/目名）
  <文件>         从文件读取筛选名称列表（每行一个）
  无筛选参数     下载当前模式下全部

示例:
  $0 -l family                                    # 查看可用的科列表
  $0 order Brassicales                           # 下载 Brassicales 目
  $0 family Fabaceae                             # 下载 Fabaceae 科
  $0 genus Oryza                                  # 下载 Oryza 属
  $0 genus Acer Arbus                             # 下载 Acer 和 Arbus 两个属
  $0 genus Oryza -i /path/to/species.txt         # 指定物种列表文件
  $0 genus species_list.txt                       # 从文件读取属名列表
  $0 order orders.txt                             # 从文件读取目名列表
  $0 all                                          # 下载全部物种
  $0 -t "Arabidopsis thaliana"                    # 测试模式：下载单个物种
  $0 all --annotated --assembly-level chromosome  # 下载有注释的染色体级别基因组
  $0 genus Oryza --reference                     # 只下载参考基因组
  $0 genus Acer -o ~/Projects/ -logdir ~/Projects/logs  # 指定下载目录和日志目录
  $0 all --assembly-source RefSeq                 # 只下载 RefSeq 来源的基因组
  $0 family Fabaceae --released-after 2020-01-01  # 下载 2020 年后发布的 Fabaceae 基因组
  $0 genus Oryza --mag exclude                   # 排除 MAG 组装
EOF
    exit 0
}

show_list() {
    local col
    case "$1" in
    order) col=6 ;;
    family) col=7 ;;
    genus) col=8 ;;
    *) col=8 ;;
    esac
    awk -F'\t' -v col="$col" 'NR>1 {print $col}' "${input_dir}" | sort | uniq -c | sort -rn
    exit 0
}

download_species() {
    local species="$1"
    local taxid="$2"
    local species_name
    species_name=$(echo "$species" | tr ' /' '_')
    species_name=${species_name%%_} # 移除尾部下划线
    local species_dir="${out_dir}/${species_name}"
    local zip_file="${species_dir}.zip"

    # 跳过无 TaxID 的物种
    if [ -z "$taxid" ] || [ "$taxid" = "-" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${species} | ${taxid:-NA} | 跳过 | 无TaxID" | tee -a "$SKIP_LOG" "$TOTAL_LOG"
        return 0
    fi

    # 检查是否已下载（解压后的文件视为已下载）
    # if [ -f "${species_dir}/${species_name}_genome.fna" ] &&
    #     [ -f "${species_dir}/${species_name}_cds.fna" ] &&
    #     [ -f "${species_dir}/${species_name}_protein.faa" ] &&
    #     [ -f "${species_dir}/${species_name}_annotation.gff" -o \
    #         -f "${species_dir}/${species_name}_annotation.gbff" ]; then
    #     # [ -f "${zip_file}" ]
    #     echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${species} | ${taxid} | 跳过 | 已存在" | tee -a "$SKIP_LOG" "$TOTAL_LOG"
    #     return 0
    # fi
    if [ -f "${species_dir}/${species_name}_genome.fna" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${species} | ${taxid} | 跳过 | 已存在基因组" | tee -a "$SKIP_LOG" "$TOTAL_LOG"
        return 0
    fi

    echo ""
    echo "============================="
    echo "下载: ${species} (TaxID: ${taxid})"
    echo "输出路径：$zip_file"
    echo "============================="
    echo ""

    # 构建 datasets download 额外参数
    local -a extra_args=()
    [ -n "$assembly_level" ] && extra_args+=(--assembly-level "$assembly_level")
    [ "$assembly_source" != "all" ] && extra_args+=(--assembly-source "$assembly_source")
    [ "$assembly_version" != "latest" ] && extra_args+=(--assembly-version "$assembly_version")
    [ "$annotated" = "yes" ] && extra_args+=(--annotated)
    [ "$reference" = "yes" ] && extra_args+=(--reference)
    [ "$exclude_atypical" = "yes" ] && extra_args+=(--exclude-atypical)
    [ "$exclude_multi_isolate" = "yes" ] && extra_args+=(--exclude-multi-isolate)
    [ "$mag" != "all" ] && extra_args+=(--mag "$mag")
    [ -n "$released_after" ] && extra_args+=(--released-after "$released_after")
    [ -n "$released_before" ] && extra_args+=(--released-before "$released_before")

    mkdir -p "$species_dir"
    datasets download genome taxon "$taxid" \
        --include "$include_types" \
        "${extra_args[@]}" \
        --filename "${zip_file}" 2>&1 | grep -v "New version"

    sleep 1

    if [ ! -f "$zip_file" ] || [ ! -s "$zip_file" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${species} | ${taxid} | 失败 | NCBI未找到" | tee -a "$FAIL_LOG" "$TOTAL_LOG"
        return 1
    fi

    if unzip -t "$zip_file"; then
        echo "解压: $species (TaxID: $taxid)"
        unzip -o "$zip_file" -d "$species_dir" >/dev/null 2>&1
        # unzip -o "$zip_file" -d "$species_dir"
        rm -f "$zip_file"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${species} | ${taxid} | 失败 | ZIP文件无效" | tee -a "$FAIL_LOG" "$TOTAL_LOG"
        rm -f "$zip_file"
        return 1
    fi

    # 整理文件：比较所有 accession，选择收录最完整的，RefSeq优先
    (
        cd "$species_dir" || exit
        find . -name "*.gz" -exec gunzip -f {} \; 2>/dev/null || true

        best_dir=""
        best_score=0

        # 遍历所有 accession 目录，计算完整性得分（RefSeq 优先：先 GCA 后 GCF）
        for dir in ncbi_dataset/data/GCF_* ncbi_dataset/data/GCA_*; do
            [ -d "$dir" ] || continue
            score=0
            is_refseq=0

            # 标记是否为 RefSeq
            [[ "$dir" == *"GCF_"* ]] && is_refseq=1

            # 文件评分
            [ -n "$(ls "$dir"/*.fna 2>/dev/null)" ] && ((score += 1))
            [ -n "$(ls "$dir"/*.cds.fna 2>/dev/null)" ] && ((score += 1))
            [ -n "$(ls "$dir"/*.faa 2>/dev/null)" ] && ((score += 1))
            [ -n "$(ls "$dir"/*.gff 2>/dev/null)" ] && ((score += 2))
            [ -n "$(ls "$dir"/*.gbff 2>/dev/null)" ] && ((score += 1))

            # 分数高 → 优先；分数相同 → GCF 优先
            if [ "$score" -gt "$best_score" ] || ([ "$score" -eq "$best_score" ] && [ "$is_refseq" -eq 1 ]); then
                best_score=$score
                best_dir="$dir"
            fi
        done

        # 复制最优版本文件
        if [ -n "$best_dir" ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${species} | ${taxid} | 选择组装版本: $best_dir" | tee -a "$TOTAL_LOG"
            cp "$best_dir"/* . 2>/dev/null
            # cp "$best_dir"/*.fna . 2>/dev/null || true
            # cp "$best_dir"/*.cds.fna . 2>/dev/null || true
            # cp "$best_dir"/*.faa . 2>/dev/null || true
            # cp "$best_dir"/*.gff . 2>/dev/null || true
            # cp "$best_dir"/*.gbff . 2>/dev/null || true
        fi

        # ====================== 安全重命名，不存在不执行 ======================
        [ ! -f "${species_name}_genome.fna" ] && mv ./GC[AF]*_genomic.fna "${species_name}_genome.fna" >/dev/null 2>&1
        [ ! -f "${species_name}_cds.fna" ] && mv ./cds_from_genomic.fna "${species_name}_cds.fna" >/dev/null 2>&1
        [ ! -f "${species_name}_protein.faa" ] && mv ./protein.faa "${species_name}_protein.faa" >/dev/null 2>&1
        [ ! -f "${species_name}_annotation.gff" ] && mv ./genomic.gff "${species_name}_annotation.gff" >/dev/null 2>&1
        [ ! -f "${species_name}_annotation.gbff" ] && mv ./genomic.gbff "${species_name}_annotation.gbff" >/dev/null 2>&1

        # ====================== 自动清理 ======================
        rm -rf ncbi_dataset/ README.md

        # 安全删除残留的原始文件（rm -f 自身可安全处理不存在的文件）
        rm -f GC[AF]*_genomic.fna cds_from_genomic.fna protein.faa genomic.gff genomic.gbff 2>/dev/null

        # ====================== 自动生成数据来源说明 ======================
        if [ -n "$best_dir" ]; then
            accession=$(basename "$best_dir")
            data_source="GenBank"
            [[ "$accession" == GCF_* ]] && data_source="RefSeq"

            cat >README_SOURCES.txt <<EOF
Species: $species
TaxID: $taxid
Assembly Accession: $accession
Data Source: $data_source
Assembly Level: $assembly_level
Download Time: $(date '+%Y-%m-%d %H:%M:%S')
Downloaded from NCBI Datasets
RefSeq: https://ftp.ncbi.nlm.nih.gov/genomes/refseq/
GenBank: https://ftp.ncbi.nlm.nih.gov/genomes/genbank/
EOF
        fi
    )

    # 检验下载文件
    if [ -f "${species_dir}/${species_name}_genome.fna" ] &&
        [ -f "${species_dir}/${species_name}_cds.fna" ] &&
        [ -f "${species_dir}/${species_name}_protein.faa" ] &&
        [ -f "${species_dir}/${species_name}_annotation.gff" ] ||
        [ -f "${species_dir}/${species_name}_annotation.gbff" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${species} | ${taxid} | 成功 | 文件完整" | tee -a "$SUCCESS_LOG" "$TOTAL_LOG"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${species} | ${taxid} | 成功 | 文件不完整" | tee -a "$SUCCESS_LOG" "$TOTAL_LOG"
        rm -f "${zip_file}"
    fi
}

# 解析参数
BATCH_MODE="genus"
BATCH_FILTERS=()
TEST_MODE="no"

# 无参数时显示帮助
if [[ $# -eq 0 ]]; then
    show_help
fi

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
    -i | --input)
        input_dir="$2"
        echo "已指定输入文件：$input_dir"
        shift
        ;;
    -o | --outdir)
        out_dir="$2"
        shift
        echo "已指定输出目录：$out_dir"
        ;;
    -logdir | --logdir)
        log_dir="$2"
        shift
        echo "已指定日志目录：$log_dir"
        ;;
    --include)
        include_types="$2"
        shift
        ;;
    --assembly-level)
        assembly_level="$2"
        shift
        ;;
    --assembly-source)
        assembly_source="$2"
        shift
        ;;
    --assembly-version)
        assembly_version="$2"
        shift
        ;;
    --annotated)
        annotated="yes"
        ;;
    --reference)
        reference="yes"
        ;;
    --exclude-atypical)
        exclude_atypical="yes"
        ;;
    --exclude-multi-isolate)
        exclude_multi_isolate="yes"
        ;;
    --mag)
        mag="$2"
        shift
        ;;
    --released-after)
        released_after="$2"
        shift
        ;;
    --released-before)
        released_before="$2"
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

mkdir -p "$out_dir" "$log_dir"

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

if [ ! -f "${input_dir}" ]; then
    echo "错误: 未找到物种列表文件 ${input_dir}" | tee -a "$TOTAL_LOG"
    exit 1
fi

# 自动检测并转换文件格式
convert_to_tsv() {
    local input="$1"
    local ext="${input##*.}"

    case "$ext" in
        xlsx|XLSX)
            echo "  检测到 Excel 格式，使用 pandas 转换..."
            python3 << PYEOF
import pandas as pd
import sys
import tempfile
df = pd.read_excel("$input")
with tempfile.NamedTemporaryFile(mode='w', suffix='.tsv', delete=False) as f:
    df.to_csv(f.name, sep='\t', index=False)
    print(f.name)
PYEOF
            ;;
        csv|CSV)
            echo "  检测到 CSV 格式..."
            python3 << PYEOF
import pandas as pd
import tempfile
try:
    df = pd.read_csv("$input")
except:
    df = pd.read_csv("$input", sep=';')
with tempfile.NamedTemporaryFile(mode='w', suffix='.tsv', delete=False) as f:
    df.to_csv(f.name, sep='\t', index=False)
    print(f.name)
PYEOF
            ;;
        *)
            echo "  检测到 TSV/TXT 格式，无需转换..."
            echo ""
            ;;
    esac
}

# 如果是 xlsx 或 csv，转换为 tsv
ext="${input_dir##*.}"
if [[ "$ext" == "xlsx" || "$ext" == "XLSX" || "$ext" == "csv" || "$ext" == "CSV" ]]; then
    echo "检测到非 TSV 格式，开始转换..."
    input_dir=$(convert_to_tsv "$input_dir")
fi

# 测试模式
if [ "$TEST_MODE" = "yes" ] && [ -n "$TEST_SPECIES" ]; then
    line=$(awk -F'\t' -v name="$TEST_SPECIES" '$2==name {print $2"\t"$3; exit}' "${input_dir}")
    species=$(echo "$line" | cut -f1)
    taxid=$(echo "$line" | cut -f2)
    download_species "$species" "$taxid"
    exit 0
fi

# 展开筛选参数：自动判断是文件还是名称
expand_filters() {
    local mode_label="$1"
    shift
    local expanded=()
    for item in "$@"; do
        if [ -f "$item" ]; then
            echo "从文件读取${mode_label}列表: $item"
            while IFS= read -r line || [[ -n "$line" ]]; do
                [[ -z "$line" || "$line" =~ ^# ]] && continue
                expanded+=("$(echo "$line" | xargs)")
            done <"$item"
        else
            expanded+=("$item")
        fi
    done
}

# 批量下载
case "$BATCH_MODE" in
order | family | genus)
    if [ "$BATCH_MODE" = "order" ]; then
        col=6
        mode_label="目名"
    elif [ "$BATCH_MODE" = "family" ]; then
        col=7
        mode_label="科名"
    else
        col=8
        mode_label="属名"
    fi
    awk -F'\t' -v col="$col" 'NR>1 {print $col}' "${input_dir}" | sort -u >/tmp/groups.txt

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
        awk -F'\t' -v g="$group" -v col="$col" '$col==g {print $2"\t"$3}' "${input_dir}" |
            while IFS=$'\t' read -r species taxid; do
                download_species "$species" "$taxid"
            done
    done
    rm -f /tmp/groups.txt
    ;;
all | "")
    awk -F'\t' 'NR>1 {print $2"\t"$3}' "${input_dir}" | sort -u |
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
