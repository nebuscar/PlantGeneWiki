#!/bin/bash
input_dir="/home/nizhu/Projects/plantsdb/sample/test"

seqkit stats "${input_dir}"/*/*.faa
head -n 2 "${input_dir}"/*/*.faa

for gff in ${input_dir}/*/*.gff; do
    d=$(dirname $gff)
    b=$(basename $gff .gff)
    bed=$d/$b.bed
    chrlist=$d/$b.chrlist
    gff2bed <$gff 2>/dev/null | awk 'BEGIN{OFS="\t"} $8=="gene"{print $1,$2,$3,$4,$5,$6}' >$bed
    cut -f1 $bed | sed -E 's/[0-9]+(\.[0-9]+)?$/N/' | sort -u >$chrlist
done

genetribe core -l sample/test/Acer_negundo/Acer_negundo -f sample/test/Acer_saccharum/Acer_saccharum
