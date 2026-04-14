#!/bin/bash
set -eo pipefail

# ===================== 基础配置 =====================
species_dir="/home/nizhu/Projects/plantsdb/sample"
output_dir="/home/nizhu/Projects/plantsdb/tmp/ready"
mkdir -p "$output_dir"
# ====================================================

echo -e "\n===== 1. 统计所有物种蛋白序列 ====="
protein_files=$(find "$species_dir" -name "*_protein.faa" | sort)

if [ -z "$protein_files" ]; then
    echo "错误：未找到任何 *_protein.faa 文件！"
    exit 1
fi
seqkit stats $protein_files 2>/dev/null

# ===================== 自动找最长序列作为参考 =====================
echo -e "\n===== 2. 自动识别参考物种（蛋白序列最长） ====="
ref_faa=$(seqkit stats $protein_files 2>/dev/null | awk 'NR>1 {
    gsub(/,/, "", $5)
    if ($5 > max) {max=$5; longest=$1}
} END {print longest}')

ref_name=$(basename "$ref_faa" _protein.faa)
echo "✅ 参考物种：$ref_name"

# ===================== 复制所有文件 =====================
echo -e "\n===== 3. 复制蛋白 / GFF / 基因组 ====="
for faa in $protein_files; do
    sp=$(basename "$faa" _protein.faa)
    gff="${faa%_protein.faa}_annotation.gff"
    fna="${faa%_protein.faa}_genome.fna"

    cp -f "$faa" "$output_dir/$sp.fa"
    cp -f "$gff" "$output_dir/$sp.gff"
    cp -f "$fna" "$output_dir/$sp.fna"
done

cd "$output_dir"

# ===================== 自动生成 3 个必需文件 =====================
echo -e "\n===== 4. 生成 BED + CHRLIST（GeneTribe 强制要求） ====="

for sp in *.fa; do
    sp=${sp%.fa}
    fa=$sp.fa
    gff=$sp.gff
    fna=$sp.fna

    echo "处理物种：$sp"

    # 1. 生成标准 BED 格式（GeneTribe 专用：chr start end geneid）
    awk '$3=="gene" {
        chr=$1; start=$4-1; end=$5; attr=$9
        sub(/.*ID=/, "", attr); sub(/;.*/, "", attr)
        print chr, start, end, attr
    }' OFS="\t" $gff >$sp.bed

    # 2. 生成 CHRLIST（通用纯ID格式：只保留 > 后第一个字符串，无多余内容）
    grep "^>" $fna | sed -E 's/^>([^[:space:]]+).*/\1/' >$sp.chrlist

    # 3. 生成基因列表（从 bed 提取，保证顺序正确）
    cut -f4 $sp.bed >$sp.gene.list
done

# ===================== 运行 GeneTribe =====================
echo -e "\n===== 5. 运行 GeneTribe 比对 ====="
for query in *.fa; do
    query=${query%.fa}
    if [ "$query" = "$ref_name" ]; then continue; fi

    echo -e "\n比对：$ref_name <-> $query"
    genetribe core -l "$ref_name" -f "$query"
done

# ===================== 完成 =====================
echo -e "\n===== ✅ 分析完成！结果如下 ====="
ls -lh *.RBH
echo -e "\n文件路径：$output_dir"
