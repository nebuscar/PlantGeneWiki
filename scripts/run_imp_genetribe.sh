#!/bin/bash
#
# run_imp_genetribe.sh
# 同属近缘物种genetribe流程
#
# 用法:
#   bash run_imp_genetribe.sh <物种代码> [输出目录]
#   bash run_imp_genetribe.sh Acam1
#   bash run_imp_genetribe.sh Acam1 ./data/imp_homolog

set -uo pipefail

# ====================== 配置 ======================
PROJECT_DIR="/home/nizhu/Projects/plantsdb"
PROTEIN_DIR="${PROJECT_DIR}/data/imp_protein"
CHRLIST_DIR="${PROJECT_DIR}/data/imp_chrlist"
BED_DIR="${PROJECT_DIR}/data/imp_gene_pos"
MANIFEST="${PROJECT_DIR}/downloads/IMP/species_manifest.tsv"
GENETRIBE="${HOME}/software/genetribe/genetribe"

usage() {
    cat <<EOF
用法: bash \$0 <物种代码> [输出目录]

同属近缘物种genetribe流程:
1. 从species_manifest获取同属物种
2. 计算各物种蛋白序列长度，选最长为参考物种
3. genetribe core -l 参考 -f 目标，逐个比对
4. 整合RBH结果，得一对一ID映射表

示例:
  bash run_imp_genetribe.sh Acam1
  bash run_imp_genetribe.sh Acam1 ./data/imp_homolog
EOF
    exit 1
}

[[ $# -lt 1 ]] && usage
QUERY="$1"
OUTPUT_DIR="${2:-${PROJECT_DIR}/data/imp_homolog}"

# ====================== 获取物种信息 ======================
get_species_name() {
    local code="$1"
    grep "^${code}" "$MANIFEST" | cut -f2
}

get_genus() {
    local species_name="$1"
    echo "$species_name" | cut -d' ' -f1
}

# ====================== 获取同属物种列表 ======================
QUERY_NAME=$(get_species_name "$QUERY")
[[ -z "$QUERY_NAME" ]] && echo "错误: 未找到物种代码 $QUERY" && exit 1
QUERY_GENUS=$(get_genus "$QUERY_NAME")

echo "查询物种: $QUERY ($QUERY_NAME)"
echo "属名: $QUERY_GENUS"

# 找出所有同属物种
declare -a GENUS_CODES=()
while IFS=$'\t' read -r code name _; do
    [[ "$code" == "Species_Code" ]] && continue
    genus=$(get_genus "$name")
    if [[ "$genus" == "$QUERY_GENUS" ]]; then
        GENUS_CODES+=("$code")
    fi
done < "$MANIFEST"

echo "同属物种: ${#GENUS_CODES[@]} 个"

# 同属物种少于2个则退出
if [[ ${#GENUS_CODES[@]} -lt 2 ]]; then
    echo "错误: 同属物种少于2个，无法进行比对"
    exit 1
fi

# ====================== 计算蛋白序列长度，选参考物种 ======================
calc_protein_length() {
    local fa="$1"
    awk 'BEGIN{len=0} /^>/{next} {len+=length($0)} END{print len}' "$fa"
}

echo "计算各物种蛋白序列长度..."
REF_CODE=""
MAX_LEN=0

for code in "${GENUS_CODES[@]}"; do
    fa="${PROTEIN_DIR}/${code}.fa"
    [[ ! -f "$fa" ]] && continue
    len=$(calc_protein_length "$fa")
    if [[ $len -gt $MAX_LEN ]]; then
        MAX_LEN=$len
        REF_CODE=$code
    fi
done

if [[ -z "$REF_CODE" ]]; then
    echo "错误: 未找到有效的参考物种"
    exit 1
fi

REF_NAME=$(get_species_name "$REF_CODE")
echo "参考物种: $REF_CODE ($REF_NAME), 蛋白总长度: $MAX_LEN"

# ====================== 批量处理 ======================
mkdir -p "$OUTPUT_DIR"

echo "开始genetribe比对..."

for code in "${GENUS_CODES[@]}"; do
    [[ "$code" == "$REF_CODE" ]] && continue

    protein="${PROTEIN_DIR}/${code}.fa"
    chrlist="${CHRLIST_DIR}/${code}.chrlist"
    bed="${BED_DIR}/${code}.bed"

    [[ ! -f "$protein" ]] && echo "警告: 跳过 $code (蛋白文件不存在)" && continue
    [[ ! -f "$chrlist" ]] && echo "警告: 跳过 $code (chrlist不存在)" && continue
    [[ ! -f "$bed" ]] && echo "警告: 跳过 $code (bed不存在)" && continue

    out_dir="${OUTPUT_DIR}/${REF_CODE}_vs_${code}"
    mkdir -p "$out_dir"

    echo "  [${REF_CODE}] vs [${code}]..."

    # 创建必要文件的符号链接
    ln -sf "${PROTEIN_DIR}/${REF_CODE}.fa" "${out_dir}/${REF_CODE}.fa"
    ln -sf "${PROTEIN_DIR}/${code}.fa" "${out_dir}/${code}.fa"
    ln -sf "${CHRLIST_DIR}/${REF_CODE}.chrlist" "${out_dir}/${REF_CODE}.chrlist"
    ln -sf "${CHRLIST_DIR}/${code}.chrlist" "${out_dir}/${code}.chrlist"
    ln -sf "${BED_DIR}/${REF_CODE}.bed" "${out_dir}/${REF_CODE}.bed"
    ln -sf "${BED_DIR}/${code}.bed" "${out_dir}/${code}.bed"

    # 在输出目录执行genetribe
    pushd "$out_dir" > /dev/null
    python3 "${GENETRIBE}" core \
        -l "$REF_CODE" \
        -f "$code" \
        -n 36 \
        2>&1 | tail -5
    popd > /dev/null
done

# ====================== 整合RBH结果 ======================
echo "整合RBH结果..."

RBH_DIR="$OUTPUT_DIR/rbh_results"
mkdir -p "$RBH_DIR"

for code in "${GENUS_CODES[@]}"; do
    [[ "$code" == "$REF_CODE" ]] && continue
    pair_dir="${OUTPUT_DIR}/${REF_CODE}_vs_${code}"
    rbh_file="${pair_dir}/${REF_CODE}_${code}.rbh"

    if [[ -f "$rbh_file" ]]; then
        awk -F'\t' '{print $1 "\t" $3}' "$rbh_file" > "${RBH_DIR}/${REF_CODE}_${code}.pair"
        echo "    $code: $(wc -l < "${RBH_DIR}/${REF_CODE}_${code}.pair") 对应关系"
    fi
done

# 合并所有pair文件
if ls "${RBH_DIR}"/*.pair 2>/dev/null | head -1 | grep -q "."; then
    cat "${RBH_DIR}"/*.pair | sort -u > "${OUTPUT_DIR}/${REF_CODE}.rbh.all.tsv"
    total=$(wc -l < "${OUTPUT_DIR}/${REF_CODE}.rbh.all.tsv")
else
    touch "${OUTPUT_DIR}/${REF_CODE}.rbh.all.tsv"
    total=0
fi

echo ""
echo "========================================"
echo "完成! 参考物种: $REF_CODE ($REF_NAME)"
echo "输出目录: $OUTPUT_DIR"
echo "总RBH映射: ${total} 对"
echo "========================================"
