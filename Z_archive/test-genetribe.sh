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
🔥 新增：自动按【属(Genus)】分组，自动做属内同源比对

Options:
  -i, --input DIR      输入目录
  -o, --output DIR     输出目录
  -q, --query SPEC     待比对物种（手动指定，优先级最高）
  -m, --mode MODE      运行模式
  -t, --threads N      GeneTribe BLAST 线程数 [默认: 36]
  --by-genus           🔥 自动按属分组运行同源分析
  -h, --help           帮助

单独参数帮助:
  ./$SCRIPT_NAME -m -h
  ./$SCRIPT_NAME -i -h

示例:
  ./$SCRIPT_NAME -m stat
  ./$SCRIPT_NAME -m faa,bed,chr
  ./$SCRIPT_NAME -m genetribe --by-genus
  ./$SCRIPT_NAME -m all --by-genus
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
PARSED_ARGS=$(getopt -o hi:o:q:m:t: --long help,input:,output:,query:,mode:,threads:,by-genus --name "$0" -- "$@")
eval set -- "$PARSED_ARGS"

INPUT_DIR=""
OUTPUT_DIR=""
QUERY_SPECIES=""
MODE="all"
THREADS=36
BY_GENUS=0

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
    -t | --threads)
        THREADS="$2"
        shift 2
        ;;
    --by-genus)
        BY_GENUS=1
        shift 1
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

# ====================== 参数校验 ======================
if ! [[ "$THREADS" =~ ^[0-9]+$ ]] || ((THREADS <= 0)); then
    echo "错误：-t/--threads 必须为正整数，当前值: $THREADS"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "========================================"
echo "输入目录: $INPUT_DIR"
echo "输出目录: $OUTPUT_DIR"
echo "运行模式: $MODE"
echo "自动按属分组: $BY_GENUS"
echo "========================================"

# ====================== 依赖检查 ======================
check_dep() { command -v "$1" &>/dev/null || {
    echo "缺少工具: $1"
    exit 1
}; }
check_dep seqkit
check_dep gff2bed
check_dep genetribe

# ====================== 全局物种列表缓存 ======================
ALL_SPECIES=()
get_all_species() {
    if [ ${#ALL_SPECIES[@]} -eq 0 ]; then
        for d in "${INPUT_DIR}"/*/; do
            sp=$(basename "$d")
            ALL_SPECIES+=("$sp")
        done
    fi
}

# ====================== 按属分组：核心函数 ======================
group_species_by_genus() {
    get_all_species
    declare -A genus_map
    for sp in "${ALL_SPECIES[@]}"; do
        genus=$(echo "$sp" | cut -d'_' -f1)
        genus_map[$genus]+="${sp} "
    done

    echo -e "\n======== 按属分组结果 ========"
    for g in $(printf '%s\n' "${!genus_map[@]}" | sort); do
        species_list=${genus_map[$g]}
        count=$(echo "$species_list" | wc -w)
        echo "🌳 $g ($count 种): $species_list"
    done

    # 输出到文件供后续使用
    mkdir -p "${OUTPUT_DIR}/group"
    >"${OUTPUT_DIR}/group/genus_map.txt"
    for g in $(printf '%s\n' "${!genus_map[@]}" | sort); do
        echo "$g: ${genus_map[$g]}" >>"${OUTPUT_DIR}/group/genus_map.txt"
    done
}

# ====================== 运行函数 ======================
run_stat() {
    seqkit_stats_out="$OUTPUT_DIR/seqkit_faa_stats.txt"
    if [[ -s "$seqkit_stats_out" ]] && [[ ${#seq_count_map[@]} -gt 0 ]]; then
        echo -e "\n[1] 序列统计已存在，跳过"
        return 0
    fi
    echo -e "\n[1] 序列统计中..."
    mkdir -p "$OUTPUT_DIR"
    find "${INPUT_DIR}" -name "*.faa" | xargs seqkit stats -T >"$seqkit_stats_out" 2>/dev/null

    # 为每个物种生成统计信息
    declare -gA seq_count_map
    while IFS=$'\t' read -r file format type sum_len min avg max num_seqs; do
        sp=$(basename $(dirname "$file"))
        seq_count_map[$sp]=$num_seqs
    done < <(tail -n +2 "$seqkit_stats_out")
}

# 为某个属自动选择参考物种
pick_ref_for_genus() {
    local genus="$1"
    local -n _pickref_list=$2 # nameref: use prefixed name to avoid collision
    local best=""
    local max=0

    for sp in "${_pickref_list[@]}"; do
        cnt=${seq_count_map[$sp]:-0}
        if ((cnt > max)); then
            max=$cnt
            best=$sp
        fi
    done
    echo "$best"
}

run_faa() {
    echo -e "\n[2] 统一蛋白ID（NCBI 专用：protein_id → locus_tag）..."
    id_map_dir="$OUTPUT_DIR/id_mapping"
    mkdir -p "$id_map_dir"

    get_all_species
    for species in "${ALL_SPECIES[@]}"; do
        species_dir="${INPUT_DIR}/${species}"
        gff=$(find "$species_dir" -name "*.gff" | head -1)
        faa=$(find "$species_dir" -name "*.faa" | head -1)
        cds=$(find "$species_dir" -name "*cds*" -name "*.fna" | head -1)
        [[ -f $gff && -f $faa ]] || continue

        id_map="$id_map_dir/${species}.map.txt"
        faa_out="$OUTPUT_DIR/${species}.faa"
        cds_out="$OUTPUT_DIR/${species}.cds"

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
            if (pid != "" && locus != "") print pid "\t" locus;
        }' "$gff" | sort -u >"$id_map"

        awk -v map="$id_map" '
        BEGIN { while((getline<map)>0) m[$1]=$2 }
        /^>/ {
            name=substr($0,2); split(name,arr,/[ \t]/); acc=arr[1];
            gsub(/\.[0-9]+$/, "", acc);
            if(acc in m) print ">",m[acc]," ",acc; else print; next
        }1' "$faa" >"$faa_out"

        if [[ -f "$cds" ]]; then
            awk -v map="$id_map" '
            BEGIN{while((getline<map)>0)m[$1]=$2}
            /^>/{
                pid=""; n=split(substr($0,2),p,/[\[\]]/);
                for(i=1;i<=n;i++)if(p[i]~/^protein_id=/){pid=substr(p[i],12);gsub(/\.[0-9]+$/,"",pid);break}
                if(pid!=""&&pid in m)print ">",m[pid]," ",pid;else print;next
            }1' "$cds" >"$cds_out"
        fi
        echo "✅ $species"
    done
}

run_bed() {
    echo -e "\n[3] GFF转BED..."
    get_all_species
    for sp in "${ALL_SPECIES[@]}"; do
        gff=$(find "${INPUT_DIR}/${sp}" -name "*.gff" | head -1)
        [[ -f "$gff" ]] || continue
        set +o pipefail
        awk -F'\t' 'NF>=9&&$5>=$4' "$gff" | gff2bed 2>/dev/null | awk '$8=="gene"' | cut -f1-6 | sed 's/\tgene-/\t/g' >"$OUTPUT_DIR/${sp}.bed"
        set -o pipefail
        if [[ ! -s "$OUTPUT_DIR/${sp}.bed" ]]; then
            awk -F'\t' '$3=="gene"&&NF>=9{
                id=""; for(i=9;i<=NF;i++)if($i~/^ID=/) {id=substr($i,4);sub(/^gene[-:]/,"",id);break}
                if(id!="") print $1"\t"$4-1"\t"$5"\t"id"\t.\t"$7
            }' "$gff" >"$OUTPUT_DIR/${sp}.bed"
        fi
        echo "✅ $sp bed 完成"
    done
}

run_chr() {
    echo -e "\n[4] 生成chrlist..."
    for bed in "$OUTPUT_DIR"/*.bed; do
        [[ -f "$bed" ]] || continue
        sp=$(basename "$bed" .bed)
        cut -f1 "$bed" | sort -u | awk 'NF' >"$OUTPUT_DIR/${sp}.chrlist"
    done
}

run_genetribe_by_genus() {
    echo -e "\n======== 启动 按属 同源分析 ========"
    group_species_by_genus
    run_stat

    local genus_file="${OUTPUT_DIR}/group/genus_map.txt"
    while IFS=': ' read -r genus species_str; do
        species_list=($species_str)
        n=${#species_list[@]}
        if ((n < 2)); then
            echo "⏭️  $genus 物种数不足2个，跳过"
            continue
        fi

        ref_sp=$(pick_ref_for_genus "$genus" species_list)
        echo -e "\n=================================================="
        echo "🌳 属：$genus"
        echo "参考物种：$ref_sp"
        echo "待比对：${species_list[@]/$ref_sp/}"
        echo "=================================================="

        for q in "${species_list[@]}"; do
            [[ "$q" == "$ref_sp" ]] && continue
            for suf in faa bed chrlist; do
                if [[ ! -f "${OUTPUT_DIR}/${ref_sp}.$suf" || ! -f "${OUTPUT_DIR}/${q}.$suf" ]]; then
                    echo "⚠️  跳过 $q：缺少文件 ${ref_sp}.$suf 或 ${q}.$suf"
                    continue 2
                fi
            done

            echo -e "\n🚀 运行 $ref_sp vs $q"
            local out_base="${OUTPUT_DIR}/by_genus/$genus"
            mkdir -p "$out_base"
            local link_dir="${OUTPUT_DIR}/by_genus/$genus"

            ln -sf "${OUTPUT_DIR}/${ref_sp}.faa" "${link_dir}/${ref_sp}.fa"
            ln -sf "${OUTPUT_DIR}/${q}.faa" "${link_dir}/${q}.fa"

            (
            cd "$link_dir"
            mkdir -p genetribe_output
            for s in "$ref_sp" "$q"; do
                ln -sf "${OUTPUT_DIR}/${s}.cds" genetribe_output/${s}.cds 2>/dev/null || true
                ln -sf "${OUTPUT_DIR}/${s}.bed" genetribe_output/${s}.bed 2>/dev/null || true
                ln -sf "${OUTPUT_DIR}/${s}.faa" genetribe_output/${s}.pep 2>/dev/null || true
            done

            local res="genetribe_${ref_sp}_vs_${q}"
            mkdir -p "$res"
            genetribe core -l "$ref_sp" -r "$q" -d "$res" -t "$THREADS" || true

            mv ./*${ref_sp}*${q}* ./*${q}*${ref_sp}* "$res/" 2>/dev/null || true
            )
        done
    done <"$genus_file"

    echo -e "\n✅ 所有属 同源分析完成！"
}

run_genetribe_original() {
    echo -e "\n[5] 运行GeneTribe（全局模式）..."
    run_stat
    # 复用 seq_count_map 选出序列数最多的物种作为参考
    local best_sp="" best_cnt=0
    for sp in "${!seq_count_map[@]}"; do
        if (( seq_count_map[$sp] > best_cnt )); then
            best_cnt=${seq_count_map[$sp]}
            best_sp=$sp
        fi
    done
    ref_sp="$best_sp"
    echo "参考物种: $ref_sp"

    if [[ -n "$QUERY_SPECIES" ]]; then
        IFS=',' read -ra qs <<<"$QUERY_SPECIES"
    else
        qs=()
        for f in "$OUTPUT_DIR"/*.faa; do
            s=$(basename "${f%.faa}")
            [[ "$s" != "$ref_sp" ]] && qs+=("$s")
        done
    fi

    for q in "${qs[@]}"; do
        echo "比对：$ref_sp vs $q"
        (
        cd "$OUTPUT_DIR"
        ln -sf "${OUTPUT_DIR}/${ref_sp}.faa" "${ref_sp}.fa" 2>/dev/null || true
        ln -sf "${OUTPUT_DIR}/${q}.faa" "${q}.fa" 2>/dev/null || true
        mkdir -p genetribe_output
        for s in "$ref_sp" "$q"; do
            ln -sf "${OUTPUT_DIR}/${s}.cds" genetribe_output/${s}.cds 2>/dev/null || true
            ln -sf "${OUTPUT_DIR}/${s}.bed" genetribe_output/${s}.bed 2>/dev/null || true
            ln -sf "${OUTPUT_DIR}/${s}.faa" genetribe_output/${s}.pep 2>/dev/null || true
        done
        out="genetribe_result/${ref_sp}_vs_${q}"
        mkdir -p "$out"
        genetribe core -l "$ref_sp" -r "$q" -d "$out" -t "$THREADS" || true
        mv ./*${ref_sp}_${q}* ./*${q}_${ref_sp}* "$out/" 2>/dev/null || true
        )
    done
}

# ====================== 执行模式 ======================
IFS=',' read -ra modes <<<"$MODE"
for m in "${modes[@]}"; do
    case "$m" in
    stat) run_stat ;;
    faa) run_faa ;;
    bed) run_bed ;;
    chr) run_chr ;;
    genetribe)
        if [[ $BY_GENUS -eq 1 ]]; then
            run_genetribe_by_genus
        else
            run_genetribe_original
        fi
        ;;
    all)
        run_stat
        run_faa
        run_bed
        run_chr
        if [[ $BY_GENUS -eq 1 ]]; then
            run_genetribe_by_genus
        else
            run_genetribe_original
        fi
        ;;
    esac
done

echo -e "\n========================================"
echo "✅ 全部任务完成！"
echo "========================================"
