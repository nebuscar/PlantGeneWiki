#!/bin/bash
input_dir="/home/nizhu/Projects/plantsdb/sample/test"
out_dir="/home/nizhu/Projects/plantsdb/genetribe_input"
mkdir -p $out_dir

# 批量处理所有物种
for gff in $input_dir/*/*.gff; do
    species=$(basename $(dirname $gff))
    faa=$input_dir/$species/${species}_protein.faa

    # 输出规范文件名
    bed=$out_dir/$species.bed
    chrlist=$out_dir/$species.chrlist
    fa=$out_dir/$species.fa

    # 1. 生成 bed
    gff2bed <$gff 2>/dev/null | awk 'BEGIN{OFS="\t"} $8=="gene"{print $1,$2,$3,$4,$5,$6}' >$bed

    # 2. 生成 chrlist
    cut -f1 $bed | sed -E 's/[0-9]+(\.[0-9]+)?$/N/' | sort -u >$chrlist

    # 3. 复制蛋白文件并重命名
    cp $faa $fa

    echo "✅ $species 处理完成！"
done

genetribe core -l Acer_negundo -f Acer_saccharum
