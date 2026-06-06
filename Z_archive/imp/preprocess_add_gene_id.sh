#!/bin/bash
#
# preprocess_add_gene_id.sh
# 为genetribe预处理蛋白质FASTA文件，从GFF3文件中提取转录本与基因ID对应关系，添加gene:前缀
#
# 用法:
#   单物种: bash preprocess_add_gene_id.sh <物种目录> <输出目录>
#   批量处理: bash preprocess_add_gene_id.sh <IMP父目录> --all
#
# 示例:
#   bash preprocess_add_gene_id.sh /DATA/data2/downloads/IMP/Acer_yangbiense ./data/imp_protein
#   bash preprocess_add_gene_id.sh /DATA/data2/downloads/IMP --all

set -uo pipefail

IMP_DATA_DIR="/DATA/data2/downloads/IMP"
OUTPUT_DIR="${HOME}/Projects/plantsdb/data/imp_protein"

usage() {
    echo "用法:"
    echo "  单物种: bash \$0 <物种目录> [输出目录]"
    echo "  批量处理: bash \$0 <IMP父目录> --all"
    echo ""
    echo "参数:"
    echo "  物种目录   包含 *.gff3.gz 和 *.prot.fasta 的物种目录"
    echo "  输出目录   处理后的FASTA文件输出目录 (默认: ${OUTPUT_DIR})"
    echo "  --all      批量处理IMP_DATA_DIR下的所有物种"
    echo ""
    echo "说明:"
    echo "  从GFF3文件中提取转录本ID与基因ID的对应关系,"
    echo "  然后为蛋白质FASTA文件的描述行添加 gene:前缀,"
    echo "  使genetribe能够正确解析基因ID"
    exit 1
}

generate_transcript_gene_map() {
    local gff3_file="$1"
    local map_file="$2"

    zcat -f "$gff3_file" | awk -F'\t' -v OFS='\t' '
        $3 == "mRNA" {
            if (match($9, /ID=([^;]+)/, arr)) {
                mrna_id = arr[1]
            }
            if (match($9, /Parent=([^;]+)/, arr)) {
                gene_id = arr[1]
                print mrna_id, gene_id
            }
        }
    ' > "$map_file"
}

process_species() {
    local species_dir="$1"
    local out_dir="$2"

    local gff3_file=""
    local prot_file=""
    local gff3_files=("${species_dir}"/*.gff3.gz)
    local prot_files=("${species_dir}"/*.prot.fasta)

    if [[ -f "${gff3_files[0]}" ]]; then
        gff3_file="${gff3_files[0]}"
    fi
    if [[ -f "${prot_files[0]}" ]]; then
        prot_file="${prot_files[0]}"
    fi

    if [[ -z "$gff3_file" ]] || [[ ! -f "$gff3_file" ]]; then
        echo "警告: GFF3文件不存在: ${species_dir}/*.gff3.gz"
        return 1
    fi
    if [[ -z "$prot_file" ]] || [[ ! -f "$prot_file" ]]; then
        echo "警告: 蛋白质FASTA文件不存在: ${species_dir}/*.prot.fasta"
        return 1
    fi

    local prefix=$(basename "$gff3_file" .gff3.gz)
    mkdir -p "$out_dir"

    local map_file=$(mktemp)
    generate_transcript_gene_map "$gff3_file" "$map_file"

    local map_count=$(wc -l < "$map_file")
    echo "[${prefix}] 转录本-基因映射: ${map_count} 条"

    local output_file="${out_dir}/${prefix}.fa"
    local temp_file=$(mktemp)
    local modified=0
    local unchanged=0

    declare -A mrna_to_gene
    while IFS=$'\t' read -r mrna gene; do
        mrna_to_gene["$mrna"]="$gene"
    done < "$map_file"

    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ "$line" =~ ^\> ]]; then
            local seq_id="${line#*>}"
            seq_id="${seq_id%% *}"

            if [[ -n "${mrna_to_gene[$seq_id]:-}" ]]; then
                local gene_id="${mrna_to_gene[$seq_id]}"
                if [[ "$line" =~ gene: ]]; then
                    unchanged=$((unchanged + 1))
                    printf '%s\n' "$line"
                else
                    modified=$((modified + 1))
                    printf '%s gene:%s\n' "$line" "$gene_id"
                fi
            else
                unchanged=$((unchanged + 1))
                printf '%s\n' "$line"
            fi
        else
            printf '%s\n' "$line"
        fi
    done < "$prot_file" > "$temp_file"

    mv "$temp_file" "$output_file"
    rm "$map_file"

    echo "[${prefix}] 完成: 添加gene: ${modified}, 已有gene: ${unchanged}, 输出: ${output_file}"
}

if [[ $# -lt 1 ]]; then
    usage
fi

INPUT="$1"

if [[ "$INPUT" == "--all" ]] || [[ "$INPUT" == "-a" ]]; then
    echo "批量处理模式: ${IMP_DATA_DIR}"
    mkdir -p "$OUTPUT_DIR"

    for species_dir in "${IMP_DATA_DIR}"/*; do
        if [[ -d "$species_dir" ]]; then
            gff3_files=("${species_dir}"/*.gff3.gz)
            if [[ -f "${gff3_files[0]}" ]] && [[ "${gff3_files[0]}" != *\** ]]; then
                process_species "$species_dir" "$OUTPUT_DIR" || true
            fi
        fi
    done
elif [[ -d "$INPUT" ]]; then
    OUTPUT_DIR="${2:-${OUTPUT_DIR}}"
    process_species "$INPUT" "$OUTPUT_DIR"
else
    echo "错误: $INPUT 不是有效的目录"
    usage
fi

echo "处理完成!"
