#!/bin/bash
set -eo pipefail

# 自动遍历 sample 下所有物种
for sp_dir in ./sample/*; do
    sp=$(basename $sp_dir)
    gff="${sp_dir}/${sp}_annotation.gff"
    bed="${sp_dir}/${sp}.bed"
    chrlist="${sp_dir}/${sp}.chr.list"

    echo -e "\n===================================="
    echo "处理物种：$sp"
    echo "GFF：$gff"
    echo -e "====================================\n"

    # 生成 BED
    python -m jcvi.formats.gff bed --type=gene --key=ID $gff -o $bed
    sed -i 's/gene://g' $bed

    # 生成 chr.list
    cut -f1 $bed | sort | uniq >$chrlist

    echo -e "✅ 生成完成：\n$bed\n$chrlist"
done

echo -e "\n🎉 所有物种 BED + chr.list 生成完毕！"
tree ./sample/
