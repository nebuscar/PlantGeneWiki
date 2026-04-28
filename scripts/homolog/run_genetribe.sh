#!/bin/bash
set -eo pipefail

# ====================== 基础配置 ======================
project_dir="/home/nizhu/Projects/plantsdb"
default_out_dir="${project_dir}/result/homolog"
default_input_dir="/DATA/data2/downloads/genomes"
input_dir="${default_input_dir}"
SCRIPT_NAME=$(basename "$0")

# ====================== 单个参数帮助 ======================
show_option_help() {
    local opt="$1"
    case "$opt" in
    -i | --input)
        cat <<EOF
参数: -i, --input DIR
功能: 指定输入目录（包含物种子文件夹，内含 *.faa 和 *.gff）
默认: $default_input_dir
示例: ./$SCRIPT_NAME -i ./data/genomes
EOF
        ;;
    -o | --output)
        cat <<EOF
参数: -o, --output DIR
功能: 指定输出目录（结果自动保存到此）
默认: $default_out_dir
示例: ./$SCRIPT_NAME -o ./result/homolog
EOF
        ;;
    -g | --genus)
        cat <<EOF
参数: -g, --genus
功能: 按属分组运行同源分析（仅同属内物种相互比对）
说明: 属名从物种目录名提取（如 Acer_saccharum → Acer）
      结果输出到属名子目录（如 result/homolog/Acer/）
      自动按属批处理，每个属独立选参考物种
      配合 -j 可多属并行
示例: ./$SCRIPT_NAME -m all -g
      ./$SCRIPT_NAME -m all -g -j 3
EOF
        ;;
    -j | --jobs)
        cat <<EOF
参数: -j, --jobs N
功能: 属并行数（-g 模式下同时处理的属数）
默认: 1（串行）
说明: 每个属使用 -t 个BLAST线程，总线程数 ≈ j × t
      建议 j×t ≤ 总CPU核数
示例: ./$SCRIPT_NAME -m all -g -j 2 -t 18  # 2属并行，每属18线程
      ./$SCRIPT_NAME -m all -g -j 3 -t 12  # 3属并行，每属12线程
EOF
        ;;
    -f | --format)
        cat <<EOF
参数: -f, --format FMT
功能: RBH合并表输出格式
可选: xlsx（默认）, csv, tsv, txt
示例: ./$SCRIPT_NAME -m merge -f csv
示例: ./$SCRIPT_NAME -m merge -f xlsx,tsv
EOF
        ;;
    -m | --mode)
        cat <<EOF
参数: -m, --mode MODE
功能: 运行模式（支持逗号分隔组合）
可选:
   all       全部运行（默认）
   stat      序列统计 + 选择参考物种
   faa       统一蛋白ID（protein_id → locus_tag，修复NCBI不匹配）
   bed       GFF 转 BED
   chr       生成 chrlist
   genetribe 运行同源分析
   merge     合并RBH映射表

示例: ./$SCRIPT_NAME -m faa,bed
EOF
        ;;
    -h | --help)
        cat <<EOF
参数: -h, --help
功能: 显示完整帮助
示例: ./$SCRIPT_NAME -h
EOF
        ;;
    *)
        echo "未知参数: $opt"
        exit 1
        ;;
    esac
    exit 0
}

# ====================== 完整帮助 ======================
usage() {
    cat <<EOF
Usage: ./$SCRIPT_NAME [OPTIONS]

植物基因组分析脚本：faa统计 + GFF转BED + chrlist + genetribe同源分析

Options:
  -i, --input DIR      输入目录
  -o, --output DIR     输出目录
  -e, --env ENV       外部conda环境路径 (包含依赖工具如seqkit等)
  -g, --genus          按属分组运行同源分析（自动批处理各属）
  -j, --jobs N         属并行数 [默认: 1]
  -m, --mode MODE      运行模式
  -f, --format FMT     RBH合并表输出格式 [默认: xlsx]
  -t, --threads N      GeneTribe BLAST 线程数 [默认: 36]
  -p, --cpus N         jcvi 共线性分析 CPU 数，0=不限制 [默认: 0]
  -h, --help           帮助

单独参数帮助:
  ./$SCRIPT_NAME -m -h
  ./$SCRIPT_NAME -i -h

示例:
  ./$SCRIPT_NAME -m stat
  ./$SCRIPT_NAME -m faa,bed,chr
  ./$SCRIPT_NAME -m merge -f csv
  ./$SCRIPT_NAME -m all -g
  ./$SCRIPT_NAME -m genetribe,merge -g
  ./$SCRIPT_NAME -m genetribe -t 16 -p 4
  ./$SCRIPT_NAME -m all -g -j 3      # 属内串行，3个属并行
EOF
}

# ====================== 帮助优先 ======================
if [[ $# -eq 2 && ("$2" == "-h" || "$2" == "--help") ]]; then
    show_option_help "$1"
fi
for arg in "$@"; do
    if [[ "$arg" == "-h" || "$arg" == "--help" ]]; then
        usage
        exit 0
    fi
done

# ====================== 无参数显示帮助 ======================
if [[ $# -eq 0 ]]; then
    usage
    exit 0
fi

# ====================== 解析参数 ======================
PARSED_ARGS=$(getopt -o hi:o:e:m:f:gj:t:p: --long help,input:,output:,env:,mode:,format:,genus,jobs:,threads:,cpus: --name "$0" -- "$@")
eval set -- "$PARSED_ARGS"

INPUT_DIR=""
OUTPUT_DIR=""
CONDA_ENV_PATH=""
MODE="all"
GENUS_MODE=false
FORMAT="xlsx"
JOBS=1
THREADS=36
CPUS=0

while true; do
    case "$1" in
    -i | --input)
        INPUT_DIR="$2"
        shift 2
        ;;
    -o | --output)
        OUTPUT_DIR="$2"
        shift 2
        ;;
    -e | --env)
        CONDA_ENV_PATH="$2"
        shift 2
        ;;
    -m | --mode)
        MODE="$2"
        shift 2
        ;;
    -f | --format)
        FORMAT="$2"
        shift 2
        ;;
    -g | --genus)
        GENUS_MODE=true
        shift
        ;;
    -j | --jobs)
        JOBS="$2"
        shift 2
        ;;
    -t | --threads)
        THREADS="$2"
        shift 2
        ;;
    -p | --cpus)
        CPUS="$2"
        shift 2
        ;;
    -h | --help)
        usage
        exit 0
        ;;
    --)
        shift
        break
        ;;
    *)
        echo "未知参数: $1"
        exit 1
        ;;
    esac
done

# ====================== 参数默认值 ======================
INPUT_DIR=${INPUT_DIR:-$default_input_dir}
OUTPUT_DIR=${OUTPUT_DIR:-$default_out_dir}

if [ ! -d "$INPUT_DIR" ]; then
    echo "错误：输入目录不存在 -> $INPUT_DIR"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "========================================"
echo "输入目录: $INPUT_DIR"
echo "输出目录: $OUTPUT_DIR"
echo "运行模式: $MODE"
if $GENUS_MODE; then echo "属分组: 开启"; fi
if $GENUS_MODE && [[ $JOBS -gt 1 ]]; then echo "属并行数: $JOBS"; fi
echo "输出格式: $FORMAT"
echo "========================================"
START_TIME=$(date +%s)

# ====================== 依赖检查 ======================
# 优先使用外部conda环境中的工具
if [[ -n "$CONDA_ENV_PATH" && -d "$CONDA_ENV_PATH/bin" ]]; then
    export PATH="$CONDA_ENV_PATH/bin:$PATH"
fi

# 添加本地安装的genetribe
GENETRIBE_LOCAL="/home/nizhu/software/genetribe"
if [[ -d "$GENETRIBE_LOCAL" ]]; then
    export PATH="$GENETRIBE_LOCAL:$PATH"
fi

check_dep() { command -v "$1" &>/dev/null || {
    echo "缺少工具: $1"
    exit 1
}; }
check_dep seqkit
check_dep genetribe

# ====================== 全局变量 ======================
# WORK_DIR: 中间文件和genetribe结果的实际输出目录
# CURRENT_GENUS: 当前正在处理的属名（-g 批处理时使用）
# CURRENT_REF: 当前参考物种名
WORK_DIR="$OUTPUT_DIR"
CURRENT_GENUS=""
CURRENT_REF=""

# ====================== 辅助函数 ======================
# 从参考物种信息文件中读取参考物种名
get_ref_sp() {
    local ref_info="$1"
    basename $(dirname $(awk -F'\t' 'NR==1{print $1}' "$ref_info"))
}

# 发现输入目录中所有有 .faa 文件的属
discover_genera() {
    local -a genera=()
    declare -A seen
    for species_dir in "${INPUT_DIR}"/*/; do
        [[ -d "$species_dir" ]] || continue
        faa=$(find "$species_dir" -name "*.faa" | head -1)
        [[ -z "$faa" ]] && continue
        sp=$(basename "$species_dir")
        genus=${sp%%_*}
        [[ -z "$genus" || -n "${seen[$genus]}" ]] && continue
        seen[$genus]=1
        genera+=("$genus")
    done
    printf '%s\n' "${genera[@]}" | sort
}

# ====================== 运行函数 ======================
# 每个 run_* 函数使用 WORK_DIR / CURRENT_GENUS / CURRENT_REF

run_stat() {
    echo -e "\n[1] 序列统计中..."
    if $GENUS_MODE; then
        # 按属独立统计，每个属选自己的参考物种
        for genus in $(discover_genera); do
            echo "  属: $genus"
            genus_dir="$OUTPUT_DIR/$genus"
            mkdir -p "$genus_dir"
            # 统计该属有 faa 的物种
            seqkit stats -T "${INPUT_DIR}/${genus}"_*/*.faa 2>/dev/null >"$genus_dir/seqkit_faa_stats.txt" || continue
            ref_info="$genus_dir/reference_species.txt"
            tail -n +2 "$genus_dir/seqkit_faa_stats.txt" | sort -t$'\t' -k4,4nr | head -1 >"$ref_info"
            ref_sp=$(get_ref_sp "$ref_info")
            ref_num=$(awk -F'\t' 'NR==1{print $4}' "$ref_info")
            echo "  参考物种: $ref_sp ($ref_num sequences)"
        done
        # 同时生成全局统计
        seqkit stats -T "${INPUT_DIR}"/*/*.faa >"$OUTPUT_DIR/seqkit_faa_stats.txt" 2>/dev/null || true
    else
        seqkit_stats_out="$OUTPUT_DIR/seqkit_faa_stats.txt"
        seqkit stats -T "${INPUT_DIR}"/*/*.faa >"$seqkit_stats_out" 2>/dev/null

        ref_info="$OUTPUT_DIR/reference_species.txt"
        tail -n +2 "$seqkit_stats_out" | sort -t$'\t' -k4,4nr | head -1 >"$ref_info"
        ref_sp=$(get_ref_sp "$ref_info")
        ref_num=$(awk -F'\t' 'NR==1{print $4}' "$ref_info")
        echo "参考物种: $ref_sp ($ref_num sequences)"
    fi
}

run_faa() {
    echo -e "\n[2] 统一蛋白ID（NCBI 专用：protein_id → locus_tag）..."
    id_map_dir="$WORK_DIR/id_mapping"
    mkdir -p "$id_map_dir"

    for species_dir in "${INPUT_DIR}"/*/; do
        species=$(basename "$species_dir")
        # -g 模式下只处理当前属
        if $GENUS_MODE && [[ -n "$CURRENT_GENUS" ]]; then
            s_genus=${species%%_*}
            [[ $s_genus != "$CURRENT_GENUS" ]] && continue
        fi

        gff=$(find "$species_dir" -name "*.gff" | head -1)
        faa=$(find "$species_dir" -name "*.faa" | head -1)
        cds=$(find "$species_dir" -name "*cds*" -name "*.fna" | head -1)
        id_map="$id_map_dir/${species}.map.txt"
        faa_out="$WORK_DIR/${species}.faa"
        cds_out="$WORK_DIR/${species}.cds"

        [[ -f $gff && -f $faa ]] || continue

        # 从 GFF 提取 protein_id 和 gene_id 的映射
        # gene行: ID=gene-xxx 和 locus_tag
        # CDS行: protein_id 和 locus_tag
        # 通过 locus_tag 关联 protein_id 和 gene_id
        awk '
        $3 == "gene" && NF >= 9 {
            gene_id = ""; locus = "";
            attrs = ""; for (i=9; i<=NF; i++) attrs = attrs (i>9?" ":"") $i;
            n = split(attrs, arr, /;/);
            for (i=1; i<=n; i++) {
                gsub(/^[ \t]+/, "", arr[i]);
                if (arr[i] ~ /^ID=gene-/) {
                    gene_id = substr(arr[i], 9);
                }
                if (arr[i] ~ /^locus_tag=/) {
                    locus = substr(arr[i], 11);
                }
            }
            if (gene_id != "" && locus != "") {
                gene_locus[locus] = gene_id;
            }
        }
        $3 == "CDS" && NF >= 9 {
            pid = ""; locus = "";
            attrs = ""; for (i=9; i<=NF; i++) attrs = attrs (i>9?" ":"") $i;
            n = split(attrs, arr, /;/);
            for (i=1; i<=n; i++) {
                gsub(/^[ \t]+/, "", arr[i]);
                if (arr[i] ~ /^protein_id=/) {
                    pid = substr(arr[i], 12);
                }
                if (arr[i] ~ /^locus_tag=/) {
                    locus = substr(arr[i], 11);
                }
            }
            if (pid != "" && locus != "" && locus in gene_locus) {
                print pid "\t" gene_locus[locus];
            }
        }' "$gff" | sort -u >"$id_map"

        # 替换 faa 文件中的 protein_id 为 locus_tag（如果映射不存在，保留原始 protein_id）
        awk -v map="$id_map" '
        BEGIN { while ((getline < map) > 0) m[$1] = $2 }
        /^>/ {
            name = substr($0, 2);
            split(name, arr, /[ \t]/);
            acc = arr[1];
            new_acc = (acc in m) ? m[acc] : acc;
            rest = (NF > 1) ? substr($0, index($0, $2)) : "";
            printf ">%s%s\n", new_acc, (rest ? " " rest : "");
            next
        }
        { print }
        ' "$faa" >"$faa_out"

        if [[ -f "$cds" ]]; then
            awk -v map="$id_map" '
            BEGIN { while ((getline < map) > 0) m[$1] = $2 }
            /^>/ {
                name = substr($0, 2);
                pid = "";
                n = split(name, parts, /[\[\]]/);
                for (i=1; i<=n; i++) {
                    if (parts[i] ~ /^protein_id=/) {
                        pid = substr(parts[i], 12);
                        gsub(/\.[0-9]+$/, "", pid);
                        break;
                    }
                }
                new_pid = (pid != "" && pid in m) ? m[pid] : pid;
                if (new_pid != "") {
                    printf ">%s protein_id=%s\n", new_pid, new_pid;
                } else {
                    print $0;
                }
                next
            }
            { print }
            ' "$cds" >"$cds_out"
        fi

        echo "✅ 处理完成：$species ($(wc -l <"$id_map") 基因已映射)"
    done
}

run_bed() {
    echo -e "\n[3] GFF转BED..."
    id_map_dir="$WORK_DIR/id_mapping"
    mkdir -p "$id_map_dir"

    for species_dir in "${INPUT_DIR}"/*/; do
        sp=$(basename "$species_dir")
        if $GENUS_MODE && [[ -n "$CURRENT_GENUS" ]]; then
            s_genus=${sp%%_*}
            [[ $s_genus != "$CURRENT_GENUS" ]] && continue
        fi
        gff=$(find "$species_dir" -name "*.gff" | head -1)
        [[ -f $gff ]] || continue

        # 使用 gene_id 作为 BED 文件中的基因 ID
        bed_out="$WORK_DIR/${sp}.bed"
        awk -F'\t' '
        $3 == "gene" && NF >= 9 {
            pid = ""; gene_id = "";
            attrs = ""; for (i=9; i<=NF; i++) attrs = attrs (i>9?" ":"") $i;
            n = split(attrs, arr, /;/);
            for (i=1; i<=n; i++) {
                gsub(/^[ \t]+/, "", arr[i]);
                if (arr[i] ~ /^protein_id=/) {
                    pid = substr(arr[i], 12);
                }
                if (arr[i] ~ /^ID=gene-/) {
                    gene_id = substr(arr[i], 9);
                }
            }
            if (gene_id != "") {
                gid = gene_id;
            } else if (pid != "") {
                gid = pid;
            } else {
                next;
            }
            start = $4 - 1;  # BED 格式起始位置为 0
            end = $5;
            strand = $7;
            print $1 "\t" start "\t" end "\t" gid "\t.\t" strand
        }
        ' "$gff" >"$bed_out"

        if [[ ! -s "$bed_out" ]]; then
            echo "⚠️  BED 为空：$sp（尝试备用提取逻辑）..."
            awk -F'\t' '$3=="gene" && NF>=9 {
                attrs = ""; for (i=9; i<=NF; i++) attrs = attrs (i>9?" ":"") $i
                n = split(attrs, a, /;/); id="";
                for (i=1; i<=n; i++) {
                    gsub(/^[ \t]+/, "", a[i]);
                    if (a[i] ~ /^ID=gene-/) { id = substr(a[i], 5); break }
                }
                if (id == "") {
                    for (i=1; i<=n; i++) {
                        gsub(/^[ \t]+/, "", a[i]);
                        if (a[i] ~ /^locus_tag=/) { id = substr(a[i], 11); break }
                    }
                }
                if (id == "") {
                    for (i=1; i<=n; i++) {
                        gsub(/^[ \t]+/, "", a[i]);
                        if (a[i] ~ /^protein_id=/) { id = substr(a[i], 12); break }
                    }
                }
                if (id != "") print $1"\t"$4-1"\t"$5"\t"id"\t.\t"$7
            }' "$gff" >"$bed_out"
        fi
        echo "✅ BED 完成：$sp ($(wc -l <"$bed_out") 条)"
    done
}

run_chr() {
    echo -e "\n[4] 生成chrlist..."
    for bed in "$WORK_DIR"/*.bed; do
        [[ -f $bed ]] || continue
        sp=$(basename "$bed" .bed)
        cut -f1 "$bed" | sort -u | awk 'NF' >"$WORK_DIR/${sp}.chrlist"
    done
}

run_genetribe() {
    echo -e "\n[5] 运行GeneTribe..."
    ref_info="$WORK_DIR/reference_species.txt"
    [[ -f $ref_info ]] || {
        echo "请先运行 -m stat"
        exit 1
    }
    ref_sp=$(get_ref_sp "$ref_info")
    ref_genus=${ref_sp%%_*}

    qs=()
    for f in "$WORK_DIR"/*.faa; do
        s=$(basename "${f%.faa}")
        if [[ $s != $ref_sp ]]; then
            if $GENUS_MODE; then
                s_genus=${s%%_*}
                [[ $s_genus == $ref_genus ]] && qs+=("$s")
            else
                qs+=("$s")
            fi
        fi
    done

    if [[ ${#qs[@]} -eq 0 ]]; then
        echo "无待比对物种"
        return
    fi
    if $GENUS_MODE; then
        echo "参考物种属: $ref_genus，同属待比对: ${qs[*]}"
    fi

    # GeneTribe 硬编码 .fa 后缀，为 .faa 创建符号链接
    for species in "$ref_sp" "${qs[@]}"; do
        faa="$WORK_DIR/${species}.faa"
        fa_link="$WORK_DIR/${species}.fa"
        [[ -f "$faa" && ! -e "$fa_link" ]] && ln -s "${species}.faa" "$fa_link"
    done

    # 激活 conda genetribe 环境
    # 尝试多种 conda 安装路径
    for conda_sh in ~/miniconda3/etc/profile.d/conda.sh ~/anaconda3/etc/profile.d/conda.sh ~/software/miniforge3/etc/profile.d/conda.sh; do
        if [[ -f "$conda_sh" ]]; then
            source "$conda_sh"
            break
        fi
    done
    if ! command -v conda &>/dev/null; then
        echo "错误：未找到 conda，请确保已安装 Miniconda 或 Anaconda"
        exit 1
    fi
    conda activate genetribe
    CONDA_ENV_DIR="$(conda info --base 2>/dev/null)/envs/genetribe"
    if [[ -d "$CONDA_ENV_DIR/bin" ]]; then
        export PATH="$CONDA_ENV_DIR/bin:$PATH"
    fi

    cd "$WORK_DIR"

    for q in "${qs[@]}"; do
        for suf in fa bed chrlist; do
            if [[ ! -f "${ref_sp}.$suf" || ! -f "${q}.$suf" ]]; then
                echo "⚠️  跳过 $q：缺少文件 ${ref_sp}.$suf 或 ${q}.$suf"
                continue 2
            fi
        done
        out="genetribe_result/${ref_sp}_vs_$q"
        mkdir -p "$out"
        mkdir -p genetribe_output
        for species in "$ref_sp" "$q"; do
            [[ -f "${species}.cds" && ! -e "genetribe_output/${species}.cds" ]] &&
                ln -s "$(pwd)/${species}.cds" "genetribe_output/${species}.cds"
            [[ -f "${species}.bed" && ! -e "genetribe_output/${species}.bed" ]] &&
                ln -s "$(pwd)/${species}.bed" "genetribe_output/${species}.bed"
            [[ -f "${species}.faa" && ! -e "genetribe_output/${species}.pep" ]] &&
                ln -s "$(pwd)/${species}.faa" "genetribe_output/${species}.pep"
        done
        genetribe core -l "$ref_sp" -f "$q" -d "$out" -n "$THREADS" || true
        result_dir="$out"
        for ext in one2one one2many RBH SBH singleton block_pos collinearity_info; do
            for f in "${ref_sp}_${q}.${ext}" "${q}_${ref_sp}.${ext}"; do
                [[ -f "$f" ]] && mv "$f" "$result_dir/"
            done
        done
        echo "完成: $ref_sp vs $q"
    done
}

run_merge() {
    echo -e "\n[6] 合并RBH映射表..."
    ref_info="$WORK_DIR/reference_species.txt"
    [[ -f $ref_info ]] || {
        echo "请先运行 -m stat"
        exit 1
    }
    ref_sp=$(get_ref_sp "$ref_info")

    # 收集所有 RBH 文件
    declare -A species_map
    for rbh in $(find "$WORK_DIR/genetribe_result" -name '*.RBH' | sort); do
        fname=$(basename "$rbh")
        dir_name=$(basename $(dirname "$rbh"))
        if [[ "$dir_name" =~ _vs_ ]]; then
            q_sp=${dir_name#*_vs_}
        else
            base=${fname%.RBH}
            if [[ "$base" == "${ref_sp}_"* ]]; then
                q_sp=${base#${ref_sp}_}
            elif [[ "$base" == *"_${ref_sp}" ]]; then
                q_sp=${base%_${ref_sp}}
            else
                q_sp=$base
            fi
        fi
        [[ "$q_sp" != "$ref_sp" ]] && species_map["$q_sp"]="$rbh"
    done

    if [[ ${#species_map[@]} -eq 0 ]]; then
        echo "未找到 RBH 文件"
        return
    fi

    sorted_species=($(printf '%s\n' "${!species_map[@]}" | sort))

    echo "参考物种: $ref_sp"
    echo "比对物种: ${sorted_species[*]}"

    merged_out="$WORK_DIR/${ref_sp%%_*}_RBH_merged.tsv"

    awk_args=()
    for sp in "${sorted_species[@]}"; do
        awk_args+=("${species_map[$sp]}")
    done

    awk -v ref_sp="$ref_sp" -v n_sp="${#sorted_species[@]}" \
        -v species_list="${sorted_species[*]}" \
        '
    BEGIN {
        FS="\t"; OFS="\t"
        split(species_list, sp_arr, " ")
        for (i = 1; i <= n_sp; i++) sp_idx[sp_arr[i]] = i
    }
    {
        sp = ""
        for (i = 1; i <= n_sp; i++) {
            if (index(FILENAME, sp_arr[i]) > 0) {
                sp = sp_arr[i]
                break
            }
        }
        if (sp == "") next
        all_genes[$1] = 1
        data[$1, sp] = $2
    }
    END {
        printf "%s", ref_sp
        for (i = 1; i <= n_sp; i++) printf OFS sp_arr[i]
        printf "\n"
        for (gene in all_genes) {
            printf "%s", gene
            for (i = 1; i <= n_sp; i++) {
                if ((gene, sp_arr[i]) in data)
                    printf OFS data[gene, sp_arr[i]]
                else
                    printf OFS "-"
            }
            printf "\n"
        }
    }
    ' "${awk_args[@]}" >"$merged_out"

    # 按参考物种基因ID排序（保留表头）
    head -1 "$merged_out" >"${merged_out}.tmp"
    tail -n +2 "$merged_out" | sort >>"${merged_out}.tmp"
    mv "${merged_out}.tmp" "$merged_out"

    echo "RBH合并完成 ($(wc -l <"$merged_out") 行)"

    base_name="${merged_out%.tsv}"
    IFS=',' read -ra fmts <<<"$FORMAT"
    keep_tsv=false
    for fmt in "${fmts[@]}"; do
        case "$fmt" in
        tsv)
            mv "$merged_out" "${base_name}.tsv"
            echo "输出: ${base_name}.tsv"
            keep_tsv=true
            ;;
        txt)
            cp "$merged_out" "${base_name}.txt"
            echo "输出: ${base_name}.txt"
            ;;
        csv)
            sed 's/\t/,/g' "$merged_out" >"${base_name}.csv"
            echo "输出: ${base_name}.csv"
            ;;
        xlsx)
            if command -v python3 &>/dev/null; then
                python3 -c "
import openpyxl, sys
wb = openpyxl.Workbook()
ws = wb.active
with open('${merged_out}') as f:
    for line in f:
        ws.append(line.rstrip('\n').split('\t'))
wb.save('${base_name}.xlsx')
" 2>/dev/null && echo "输出: ${base_name}.xlsx" || {
                    echo "xlsx输出失败（需 openpyxl），回退到csv"
                    sed 's/\t/,/g' "$merged_out" >"${base_name}.csv"
                    echo "输出: ${base_name}.csv"
                }
            else
                echo "python3 不可用，xlsx输出跳过，回退到csv"
                sed 's/\t/,/g' "$merged_out" >"${base_name}.csv"
                echo "输出: ${base_name}.csv"
            fi
            ;;
        *)
            echo "未知格式: $fmt，跳过"
            ;;
        esac
    done

    # 清理临时tsv（未被mv走则删除）
    [[ -f "$merged_out" ]] && rm "$merged_out"
}

# ====================== 执行模式 ======================
# run_pipeline: 在给定 WORK_DIR 下执行指定步骤
run_pipeline() {
    local steps="$1"
    IFS=',' read -ra ms <<<"$steps"
    for m in "${ms[@]}"; do
        case "$m" in
        stat) run_stat ;;
        faa) run_faa ;;
        bed) run_bed ;;
        chr) run_chr ;;
        genetribe) run_genetribe ;;
        merge) run_merge ;;
        all)
            run_stat
            run_faa
            run_bed
            run_chr
            run_genetribe
            run_merge
            ;;
        esac
    done
}

if $GENUS_MODE; then
    # ========== -g 批处理模式 ==========
    # stat 特殊：需要先全局跑一次，按属选参考
    IFS=',' read -ra modes <<<"$MODE"
    need_stat=false
    other_steps=""
    for m in "${modes[@]}"; do
        case "$m" in
        stat) need_stat=true ;;
        all)
            need_stat=true
            other_steps="faa,bed,chr,genetribe,merge"
            ;;
        faa | bed | chr | genetribe | merge) other_steps="${other_steps:+$other_steps,}$m" ;;
        esac
    done

    # 1) 先跑 stat（按属独立选参考）
    if $need_stat; then
        run_stat
    fi

    # 2) 收集可处理的属
    valid_genera=()
    for genus in $(discover_genera); do
        genus_dir="$OUTPUT_DIR/$genus"
        ref_info="$genus_dir/reference_species.txt"
        if [[ ! -f "$ref_info" ]]; then
            echo "跳过属 $genus：无参考物种信息"
            continue
        fi
        faa_count=0
        for f in "$INPUT_DIR/${genus}"_*/*.faa; do
            [[ -f "$f" ]] && faa_count=$((faa_count + 1))
        done
        if [[ $faa_count -lt 2 ]]; then
            echo "跳过属 $genus：只有 $faa_count 个物种有蛋白序列，无法比对"
            continue
        fi
        valid_genera+=("$genus")
    done

    echo ""
    echo "待处理属: ${valid_genera[*]} (共 ${#valid_genera[@]} 个)"

    # 3) 属处理函数（供串行/并行调用）
    process_genus() {
        local genus="$1"
        local genus_dir="$OUTPUT_DIR/$genus"
        local ref_info="$genus_dir/reference_species.txt"
        local ref_sp=$(get_ref_sp "$ref_info")

        echo ""
        echo "########################################"
        echo "  处理属: $genus（参考物种: $ref_sp）"
        echo "########################################"

        local GENUS_START=$(date +%s)
        CURRENT_GENUS="$genus"
        CURRENT_REF="$ref_sp"
        WORK_DIR="$genus_dir"
        mkdir -p "$WORK_DIR"

        run_pipeline "$other_steps"

        local GENUS_END=$(date +%s)
        local GENUS_ELAPSED=$((GENUS_END - GENUS_START))
        echo "  属 $genus 完成，耗时: ${GENUS_ELAPSED}s"
    }

    # 4) 执行：串行或并行
    if [[ $JOBS -le 1 ]]; then
        # 串行
        for genus in "${valid_genera[@]}"; do
            process_genus "$genus"
        done
    else
        # 并行：导出函数和变量，用 xargs 调度
        export -f process_genus run_pipeline run_stat run_faa run_bed run_chr run_genetribe run_merge get_ref_sp discover_genera
        export INPUT_DIR OUTPUT_DIR MODE FORMAT THREADS CPUS other_steps CURRENT_GENUS CURRENT_REF WORK_DIR
        printf '%s\n' "${valid_genera[@]}" | xargs -P "$JOBS" -I{} bash -c 'process_genus "$@"' _ {}
    fi
else
    # ========== 非 -g 模式（原行为） ==========
    run_pipeline "$MODE"
fi

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
HOURS=$((ELAPSED / 3600))
MINS=$(((ELAPSED % 3600) / 60))
SECS=$((ELAPSED % 60))

echo -e "\n========================================"
echo "✅ 运行完成，总耗时: ${HOURS}h ${MINS}m ${SECS}s"
echo "========================================"
