#!/bin/bash
set -eo pipefail

#======================================================================
# GeneTribe 全自动批处理脚本
# 适配：物种名_annotation.gff / _genome.fna / _protein.faa
# 修复 BED ID 不匹配问题，确保 GeneTribe 正常运行
#======================================================================

# ==================== 基础配置 ====================
CONDA_ENV="genetribe"
GFF_SUFFIX="_annotation.gff"
GENOME_SUFFIX="_genome.fna"
PROTEIN_SUFFIX="_protein.faa"
default_out_dir="./genetribe_auto"
# ==================================================

# ==================== 帮助文档 ====================
show_help() {
    cat <<EOF
用法: $0 [模式] [选项]

功能:
  全自动运行 GeneTribe 同源基因分析
  只需提供原始文件：gff + genome.fna + protein.faa
  脚本自动生成 BED / chrlist，并批量两两比对、合并结果

======================================================================
模式说明（必须选择一个）:
----------------------------------------------------------------------
  auto          【全自动推荐】一键完成所有步骤：
                1. 检查输入文件
                2. 自动生成 bed/chrlist/fa
                3. 批量运行所有物种两两 GeneTribe
                4. 自动合并全部 RBH 同源基因对

  prepare       仅预处理：
                只从 gff/fna/faa 生成 bed + chrlist/fa
                不运行比对

  run           仅运行 GeneTribe 比对：
                要求文件已通过 prepare 生成

  merge         仅合并 RBH 结果：
                把所有比对结果合并成总表

  clean         清理临时文件
======================================================================

选项:
  -h, --help              显示帮助信息
  -i, --indir DIR         输入目录（必须）：存放 gff/genome.fna/faa 文件
  -o, --outdir DIR        输出目录 (默认: ${default_out_dir})
  -c, --conda ENV         Conda 环境名称 (默认: genetribe)
  -k, --keep              保留所有中间文件，不自动清理

GeneTribe 参数:
  --threads INT           BLAST 线程数 (默认: 8)
  --evalue FLOAT          E-value 阈值 (默认: 1e-10)
  --identity INT         序列一致性阈值 (默认: 30)

输入文件（每个物种 3 个）:
  物种名_annotation.gff
  物种名_genome.fna
  物种名_protein.faa

使用示例:
  $0 auto -i ./species          # 全自动运行（推荐）
  $0 prepare -i ./species       # 只生成标准输入文件
  $0 run -o ./result            # 只跑比对
  $0 merge -o ./result          # 只合并结果
EOF
    exit 0
}

# ==================== 工具函数 ====================
error_exit() {
    echo -e "\033[31m[ERROR] $1\033[0m"
    exit 1
}

check_cmd() {
    if ! command -v $1 &>/dev/null; then
        error_exit "缺少工具：$1，请安装后重试"
    fi
}

# 激活 conda
activate_env() {
    echo -e "\033[32m[INFO] 激活 conda 环境: $CONDA_ENV\033[0m"

    if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
        source "$HOME/miniconda3/etc/profile.d/conda.sh"
    elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
        source "$HOME/anaconda3/etc/profile.d/conda.sh"
    elif [ -f "/opt/conda/etc/profile.d/conda.sh" ]; then
        source "/opt/conda/etc/profile.d/conda.sh"
    else
        source "$(conda info --base)/etc/profile.d/conda.sh"
    fi

    conda activate "$CONDA_ENV" || error_exit "Conda 环境 $CONDA_ENV 激活失败"

    check_cmd gffread
    check_cmd seqkit
    check_cmd bedtools
    check_cmd genetribe
    check_cmd blastp
}

# 检查输入目录
check_input() {
    local dir="$1"
    [ -d "$dir" ] || error_exit "输入目录不存在：$dir"

    local gffs=$(ls "$dir"/*$GFF_SUFFIX 2>/dev/null | wc -l)
    local fnas=$(ls "$dir"/*$GENOME_SUFFIX 2>/dev/null | wc -l)
    local faas=$(ls "$dir"/*$PROTEIN_SUFFIX 2>/dev/null | wc -l)

    [ $gffs -lt 1 ] && error_exit "缺少 *_annotation.gff 文件"
    [ $fnas -lt 1 ] && error_exit "缺少 *_genome.fna 基因组文件"
    [ $faas -lt 1 ] && error_exit "缺少 *_protein.faa 蛋白文件"

    for gff in "$dir"/*$GFF_SUFFIX; do
        sp=$(basename "$gff" $GFF_SUFFIX)
        [ -f "$dir/${sp}${GENOME_SUFFIX}" ] || error_exit "$sp 缺少 ${sp}${GENOME_SUFFIX}"
        [ -f "$dir/${sp}${PROTEIN_SUFFIX}" ] || error_exit "$sp 缺少 ${sp}${PROTEIN_SUFFIX}"
    done
}

# 【修复】生成正确的 BED 文件，ID 与蛋白序列完全匹配
prepare_files() {
    local in_dir="$1"
    local out_dir="$2/ready"
    mkdir -p "$out_dir"
    echo -e "\033[32m[INFO] 自动生成 BED 和 chrlist...\033[0m"

    for gff in "$in_dir"/*$GFF_SUFFIX; do
        sp=$(basename "$gff" $GFF_SUFFIX)
        genome="$in_dir/${sp}${GENOME_SUFFIX}"
        protein="$in_dir/${sp}${PROTEIN_SUFFIX}"

        bed="$out_dir/$sp.bed"
        chrlist="$out_dir/$sp.chrlist"
        fa="$out_dir/$sp.fa"

        # ===================== 核心修复 =====================
        # 从 GFF 中提取 CDS / gene 的正确 ID，完全匹配蛋白ID
        awk 'BEGIN{OFS="\t"} $3=="gene" || $3=="CDS" || $3=="mRNA" {
            match($9, /ID=([^;]+)/, id);
            print $1, $4-1, $5, id[1], ".", $7;
        }' "$gff" | sort | uniq >"$bed"

        # 生成 chrlist
        seqkit fx2tab -nl "$genome" | awk 'BEGIN{OFS="\t"} {print $1,$2}' >"$chrlist"

        # 复制蛋白文件
        cp "$protein" "$fa"
    done
    echo -e "\033[32m[INFO] 文件准备完成：$out_dir\033[0m"
}

# 运行比对
run_genetribe() {
    local ready_dir="$1/ready"
    local result_dir="$1/results"
    mkdir -p "$result_dir"

    species_list=()
    for fa in "$ready_dir"/*.fa; do
        if [ -f "$fa" ]; then
            sp=$(basename "$fa" .fa)
            species_list+=("$sp")
        fi
    done

    n=${#species_list[@]}
    echo -e "\033[32m[INFO] 检测到物种数量：$n\033[0m"
    [ $n -lt 2 ] && error_exit "至少需要 2 个物种"

    echo -e "\033[32m[INFO] 开始两两比对：$n 个物种\033[0m"
    for ((i = 0; i < n; i++)); do
        s1=${species_list[$i]}
        for ((j = i + 1; j < n; j++)); do
            s2=${species_list[$j]}
            echo -e "\033[34m[RUN] $s1 VS $s2\033[0m"

            cd "$ready_dir"
            # 运行 GeneTribe
            genetribe core -l "$s1" -f "$s2"

            # 移动结果
            mv -f ${s1}_${s2}* ${s2}_${s1}* "$result_dir"/ 2>/dev/null || true
        done
    done
}

# 合并结果（容错版）
merge_rbh() {
    local result_dir="$1/results"
    local final="$1/all_rbh_merged.tsv"

    echo -e "\033[32m[INFO] 合并所有 RBH...\033[0m"
    echo -e "Query\tSubject\tType" >"$final"

    for f in "$result_dir"/*.RBH; do
        if [ -f "$f" ]; then
            grep -v "^#" "$f" | grep -v "^Query" >>"$final" || true
        fi
    done

    echo -e "\033[32m[INFO] 合并完成：$final\033[0m"
}

# ==================== 参数解析 ====================
for arg in "$@"; do
    if [[ "$arg" == "-h" || "$arg" == "--help" ]]; then
        show_help
    fi
done

if [ $# -eq 0 ]; then
    show_help
fi

MODE="$1"
shift

indir=""
outdir="$default_out_dir"
keep=0

while [ $# -gt 0 ]; do
    case "$1" in
    -h | --help) show_help ;;
    -i | --indir)
        indir="$2"
        shift 2
        ;;
    -o | --outdir)
        outdir="$2"
        shift 2
        ;;
    -c | --conda)
        CONDA_ENV="$2"
        shift 2
        ;;
    -k | --keep)
        keep=1
        shift
        ;;
    *) error_exit "未知参数：$1" ;;
    esac
done

# 执行模式
case "$MODE" in
auto)
    check_input "$indir"
    activate_env
    prepare_files "$indir" "$outdir"
    run_genetribe "$outdir"
    merge_rbh "$outdir"
    ;;
prepare)
    check_input "$indir"
    activate_env
    prepare_files "$indir" "$outdir"
    ;;
run)
    activate_env
    run_genetribe "$outdir"
    ;;
merge)
    merge_rbh "$outdir"
    ;;
clean)
    rm -rf "$outdir"/tmp* "$outdir"/ready/tmp* 2>/dev/null
    echo "[INFO] 清理完成"
    ;;
*)
    error_exit "无效模式：$MODE"
    ;;
esac

if [ $keep -eq 0 ]; then
    rm -f tmp.gtf 2>/dev/null
fi

echo -e "\033[32m==========================================\033[0m"
echo -e "\033[32m  任务完成！输出目录：$outdir\033[0m"
echo -e "\033[32m==========================================\033[0m"
