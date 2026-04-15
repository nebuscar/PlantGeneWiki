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
    -q | --query)
        cat <<EOF
参数: -q, --query SPEC
功能: 指定待比对物种名称（可指定多个，逗号分隔）
说明: 不指定则自动以所有非参考物种作为待比对物种
示例: ./$SCRIPT_NAME -q Acer_saccharum
示例: ./$SCRIPT_NAME -q "Acer_saccharum,Acer_rubrum"
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
  -q, --query SPEC     待比对物种
  -m, --mode MODE      运行模式
  -h, --help           帮助

单独参数帮助:
  ./$SCRIPT_NAME -m -h
  ./$SCRIPT_NAME -i -h

示例:
  ./$SCRIPT_NAME -m stat
  ./$SCRIPT_NAME -m faa,bed,chr
  ./$SCRIPT_NAME -m genetribe -q Acer_saccharum
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

# ====================== 解析参数 ======================
PARSED_ARGS=$(getopt -o hi:o:q:m: --long help,input:,output:,query:,mode: --name "$0" -- "$@")
eval set -- "$PARSED_ARGS"

INPUT_DIR=""
OUTPUT_DIR=""
QUERY_SPECIES=""
MODE="all"

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
    -q | --query)
        QUERY_SPECIES="$2"
        shift 2
        ;;
    -m | --mode)
        MODE="$2"
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
echo "========================================"

# ====================== 依赖检查 ======================
check_dep() { command -v "$1" &>/dev/null || {
    echo "缺少工具: $1"
    exit 1
}; }
check_dep seqkit
check_dep gff2bed
check_dep genetribe

# ====================== 运行函数 ======================
run_stat() {
    echo -e "\n[1] 序列统计中..."
    seqkit_stats_out="$OUTPUT_DIR/seqkit_faa_stats.txt"
    seqkit stats -T "${INPUT_DIR}"/*/*.faa >"$seqkit_stats_out" 2>/dev/null

    ref_info="$OUTPUT_DIR/reference_species.txt"
    tail -n +2 "$seqkit_stats_out" | sort -t$'\t' -k4,4nr | head -1 >"$ref_info"
    ref_sp=$(basename $(dirname $(awk -F'\t' 'NR==1{print $1}' "$ref_info")))
    ref_num=$(awk -F'\t' 'NR==1{print $4}' "$ref_info")
    echo "参考物种: $ref_sp ($ref_num sequences)"
}

run_faa() {
    echo -e "\n[2] 统一蛋白ID（NCBI 专用：protein_id → locus_tag）..."
    id_map_dir="$OUTPUT_DIR/id_mapping"
    mkdir -p "$id_map_dir"

    for species_dir in "${INPUT_DIR}"/*/; do
        species=$(basename "$species_dir")
        gff=$(find "$species_dir" -name "*.gff" | head -1)
        faa=$(find "$species_dir" -name "*.faa" | head -1)
        cds=$(find "$species_dir" -name "*cds*" -name "*.fna" | head -1)
        id_map="$id_map_dir/${species}.map.txt"
        faa_out="$OUTPUT_DIR/${species}.faa"
        cds_out="$OUTPUT_DIR/${species}.cds"

        [[ -f $gff && -f $faa ]] || continue

        # 🔥 终极正确匹配：只抓 protein_id 和 locus_tag
        # 注意：NCBI GFF 属性列可能含空格（如 product=hypothetical protein），
        #       导致 awk 将属性拆到多个字段，需合并 $9..$NF 后再解析
        awk '
        $3 == "CDS" {
            pid = ""; locus = "";
            attrs = ""; for (i=9; i<=NF; i++) attrs = attrs (i>9?" ":"") $i;
            n = split(attrs, arr, /;/);
            for (i=1; i<=n; i++) {
                gsub(/^[ \t]+/, "", arr[i]);
                if (arr[i] ~ /^protein_id=/) {
                    pid = substr(arr[i], 12);
                    gsub(/\.[0-9]+$/, "", pid);
                }
                if (arr[i] ~ /^locus_tag=/) {
                    locus = substr(arr[i], 11);
                }
            }
            if (pid != "" && locus != "") {
                print pid "\t" locus;
            }
        }' "$gff" | sort -u >"$id_map"

        # 替换 FAA 标题：protein_id → locus_tag
        awk -v map="$id_map" '
        BEGIN { while ((getline < map) > 0) m[$1] = $2 }
        /^>/ {
            name = substr($0, 2);
            split(name, arr, /[ \t]/);
            acc = arr[1];
            gsub(/\.[0-9]+$/, "", acc);
            if (acc in m) {
                print ">" m[acc] " " acc;
            } else {
                print $0;
            }
            next;
        }
        { print }
        ' "$faa" >"$faa_out"

        # 替换 CDS 标题：从 lcl|..._cds_PROTEINID_... 格式提取 protein_id 并替换
        # NCBI CDS FASTA 头格式: >lcl|Chr_cds_PROTEINID_1 [protein=...] [protein_id=PROTEINID] ...
        if [[ -f "$cds" ]]; then
            awk -v map="$id_map" '
            BEGIN { while ((getline < map) > 0) m[$1] = $2 }
            /^>/ {
                # 从 [protein_id=XXX] 中提取 protein_id
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
                if (pid != "" && pid in m) {
                    print ">" m[pid] " " pid;
                } else {
                    print $0;
                }
                next;
            }
            { print }
            ' "$cds" >"$cds_out"
        fi

        echo "✅ 处理完成：$species"
    done
}

run_bed() {
    echo -e "\n[3] GFF转BED..."
    for species_dir in "${INPUT_DIR}"/*/; do
        sp=$(basename "$species_dir")
        gff=$(find "$species_dir" -name "*.gff" | head -1)
        [[ -f $gff ]] || continue
        # gff2bed 遇到坐标异常（end < start）会中止并报错，
        # 用 awk 预过滤掉坐标异常行，避免中断流水线
        # 临时关闭 pipefail 以容忍 gff2bed 的非零退出
        set +o pipefail
        awk -F'\t' 'NF>=9 && $5>=$4' "$gff" | gff2bed 2>/dev/null | awk '$8=="gene"' OFS="\t" >"$OUTPUT_DIR/${sp}.bed"
        set -o pipefail
        if [[ ! -s "$OUTPUT_DIR/${sp}.bed" ]]; then
            echo "⚠️  BED 为空：$sp（gff2bed 可能失败），尝试 awk 直接转换..."
            awk -F'\t' '$3=="gene" && NF>=9 {
                attrs = ""; for (i=9; i<=NF; i++) attrs = attrs (i>9?" ":"") $i
                n = split(attrs, a, /;/); id="";
                for (i=1; i<=n; i++) {
                    gsub(/^[ \t]+/, "", a[i]);
                    if (a[i] ~ /^ID=/) { id = substr(a[i], 4); sub(/^gene:/, "", id); break }
                }
                if (id != "") print $1"\t"$4-1"\t"$5"\t"id"\t.\t"$7
            }' "$gff" >"$OUTPUT_DIR/${sp}.bed"
        fi
        echo "✅ BED 完成：$sp ($(wc -l <"$OUTPUT_DIR/${sp}.bed") 条)"
    done
}

run_chr() {
    echo -e "\n[4] 生成chrlist..."
    for bed in "$OUTPUT_DIR"/*.bed; do
        [[ -f $bed ]] || continue
        sp=$(basename "$bed" .bed)
        cut -f1 "$bed" | sort -u | awk 'NF' >"$OUTPUT_DIR/${sp}.chrlist"
    done
}

run_genetribe() {
    echo -e "\n[5] 运行GeneTribe..."
    ref_info="$OUTPUT_DIR/reference_species.txt"
    [[ -f $ref_info ]] || {
        echo "请先运行 -m stat"
        exit 1
    }
    ref_sp=$(basename $(dirname $(awk -F'\t' 'NR==1{print $1}' "$ref_info")))

    if [[ -n $QUERY_SPECIES ]]; then
        IFS=',' read -ra qs <<<"$QUERY_SPECIES"
    else
        qs=()
        for f in "$OUTPUT_DIR"/*.faa; do
            s=$(basename "${f%.faa}")
            [[ $s != $ref_sp ]] && qs+=("$s")
        done
    fi

    # GeneTribe 硬编码 .fa 后缀，为 .faa 创建符号链接
    for species in "$ref_sp" "${qs[@]}"; do
        faa="$OUTPUT_DIR/${species}.faa"
        fa_link="$OUTPUT_DIR/${species}.fa"
        [[ -f "$faa" && ! -e "$fa_link" ]] && ln -s "${species}.faa" "$fa_link"
    done

    # 激活 conda genetribe 环境，确保 jcvi 可用
    eval "$(conda shell.bash hook 2>/dev/null)"
    conda activate genetribe

    # 保存当前目录，GeneTribe 基于工作目录查找前缀文件
    local orig_dir="$(pwd)"
    cd "$OUTPUT_DIR"

    for q in "${qs[@]}"; do
        for suf in fa bed chrlist; do
            [[ -f "${ref_sp}.$suf" && -f "${q}.$suf" ]] || continue 2
        done
        out="genetribe_result/${ref_sp}_vs_$q"
        mkdir -p "$out"
        # GeneTribe 运行时会在 genetribe_output/ 中调用 jcvi，
        # 先将 .cds 链接到该目录以便共线性分析使用
        genetribe core -l "$ref_sp" -f "$q" -d "$out" || true
        if [[ -d "genetribe_output" ]]; then
            for species in "$ref_sp" "$q"; do
                [[ -f "${species}.cds" && ! -e "genetribe_output/${species}.cds" ]] && \
                    ln -s "$(pwd)/${species}.cds" "genetribe_output/${species}.cds"
            done
            cd genetribe_output
            set +eo pipefail
            python -m jcvi.compara.catalog ortholog --no_strip_names "$ref_sp" "$q"
            set -eo pipefail
            cd ..
        fi
        echo "完成: $ref_sp vs $q"
    done

    cd "$orig_dir"
}

# ====================== 执行模式 ======================
IFS=',' read -ra modes <<<"$MODE"
for m in "${modes[@]}"; do
    case "$m" in
    stat) run_stat ;;
    faa) run_faa ;;
    bed) run_bed ;;
    chr) run_chr ;;
    genetribe) run_genetribe ;;
    all)
        run_stat
        run_faa
        run_bed
        run_chr
        run_genetribe
        ;;
    esac
done

echo -e "\n========================================"
echo "✅ 运行完成"
echo "========================================"
