#!/bin/bash
set -eo pipefail

# ====================== 基础配置 ======================
project_dir="/home/nizhu/Projects/plantsdb"
meta_dir="${project_dir}/data/meta/species_list_with_taxid.txt"
default_out_dir="${project_dir}/result/homolog"
default_input_dir="${project_dir}/downloads/genomes"

# ====================== 帮助信息 ======================
usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

植物基因组分析脚本：faa序列统计 + GFF转BED + 染色体列表 + genetribe同源基因分析

Options:
  -i, --input DIR      输入目录（包含物种子文件夹，内含 *.faa 和 *.gff）
                        默认: $default_input_dir
  -o, --output DIR     输出目录（结果自动保存到此）
                        默认: $default_out_dir
  -h, --help           显示帮助信息并退出

示例:
  ./$0 -i /path/to/input -o /path/to/output
  ./$0 --help
EOF
}

# ====================== 解析命令行参数 ======================
PARSED_ARGS=$(getopt -o hi:o: --long help,input:,output: --name "$0" -- "$@")
if [ $? -ne 0 ]; then
    echo "参数解析失败！"
    exit 1
fi
eval set -- "$PARSED_ARGS"

INPUT_DIR=""
OUTPUT_DIR=""

while true; do
    case "$1" in
    -h | --help)
        usage
        exit 0
        ;;
    -i | --input)
        INPUT_DIR="$2"
        shift 2
        ;;
    -o | --output)
        OUTPUT_DIR="$2"
        shift 2
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
if [ -z "$INPUT_DIR" ]; then
    INPUT_DIR="$default_input_dir"
fi
if [ -z "$OUTPUT_DIR" ]; then
    OUTPUT_DIR="$default_out_dir"
fi

if [ ! -d "$INPUT_DIR" ]; then
    echo "错误：输入目录不存在 -> $INPUT_DIR"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"
echo "========================================"
echo "  脚本开始运行"
echo "  输入目录: $INPUT_DIR"
echo "  输出目录: $OUTPUT_DIR"
echo "========================================"
echo ""

# ====================== 依赖检查 ======================
echo "===== 检查依赖工具 ====="
check_dep() {
    if ! command -v "$1" &>/dev/null; then
        echo "错误：未找到依赖工具 -> $1"
        exit 1
    fi
}
check_dep seqkit
check_dep gff2bed
check_dep genetribe
echo "✅ 所有依赖工具检查通过"
echo ""

# ====================== 1. 序列统计 ======================
echo "===== 1. 运行 seqkit 蛋白序列统计 ====="
seqkit_stats_out="$OUTPUT_DIR/seqkit_faa_stats.txt"
seqkit stats "${INPUT_DIR}"/*/*.faa >"$seqkit_stats_out" 2>/dev/null
echo "✅ seqkit 统计结果: $seqkit_stats_out"

preview_dir="$OUTPUT_DIR/faa_preview"
mkdir -p "$preview_dir"
for faa in "${INPUT_DIR}"/*/*.faa; do
    sp=$(basename "$(dirname "$faa")")
    head -n 4 "$faa" >"$preview_dir/${sp}_preview.txt"
done
echo "✅ 所有物种 faa 预览已保存: $preview_dir"
echo ""

# ====================== 【新增】自动选择 num_seqs 最多的物种作为参考 ======================
echo "===== 1.1 自动识别参考物种（序列数最多 num_seqs） ====="
ref_info="$OUTPUT_DIR/reference_species.txt"

# 从seqkit结果中提取：num_seqs最多的文件路径
tail -n +2 "$seqkit_stats_out" | sort -k4,4nr | head -1 >"$ref_info"
ref_faa=$(cat "$ref_info" | awk '{print $1}')
ref_sp=$(basename $(dirname "$ref_faa"))
ref_num_seqs=$(cat "$ref_info" | awk '{print $4}')

# 记录参考信息
echo "参考物种faa文件: $ref_faa" >>"$ref_info"
echo "参考物种名称: $ref_sp" >>"$ref_info"
echo "序列总数 num_seqs: $ref_num_seqs" >>"$ref_info"

echo "✅ 已自动选择参考物种: $ref_sp (num_seqs = $ref_num_seqs)"
echo "✅ 参考信息已保存: $ref_info"
echo ""

# ====================== 2. GFF 转 BED ======================
echo "===== 2. GFF → BED 格式转换 + 染色体列表 ====="
gff_files=$(find "$INPUT_DIR" -name "*.gff" | wc -l)
if [ "$gff_files" -eq 0 ]; then
    echo "⚠️  未找到 GFF 文件，跳过转换"
else
    for gff in "${INPUT_DIR}"/*/*.gff; do
        d=$(dirname "$gff")
        base=$(basename "$gff" .gff)
        species=$(basename "$d")

        bed="$OUTPUT_DIR/${species}.bed"
        chrlist="$OUTPUT_DIR/${species}.chrlist"

        gff2bed <"$gff" 2>/dev/null | awk '$8=="gene" {print $1,$2,$3,$4,$5,$6}' OFS="\t" >"$bed"
        cut -f1 "$bed" | sed -E 's/[0-9]+(\.[0-9]+)?$/N/' | sort -u | grep -v '^$' >"$chrlist"

        echo "✅ 处理完成：$species"
    done
fi
echo ""

# ====================== 3. genetribe core ======================
echo "===== 3. 运行 genetribe 同源基因 BBH 分析 ====="
genetribe_out="$OUTPUT_DIR/genetribe_bbh"
mkdir -p "$genetribe_out"
log_file="$OUTPUT_DIR/genetribe_run.log"

# ====================== 【可修改】近缘物种前缀 ======================
sp1_prefix="Acer_negundo"
sp2_prefix="Acer_saccharum"

sp1_path="${INPUT_DIR}/${sp1_prefix}/${sp1_prefix}"
sp2_path="${INPUT_DIR}/${sp2_prefix}/${sp2_prefix}"

if [ ! -f "${sp1_path}.faa" ] || [ ! -f "${sp2_path}.faa" ]; then
    echo "错误：genetribe 输入文件不存在，请检查物种名称和路径"
    exit 1
fi

genetribe core \
    -l "$sp1_path" \
    -f "$sp2_path" \
    -o "$genetribe_out" \
    >"$log_file" 2>&1

echo "✅ genetribe 分析完成"
echo "📄 运行日志: $log_file"
echo "📂 结果目录: $genetribe_out"
echo ""

# ====================== 结束 ======================
echo "========================================"
echo "🎉 脚本全部运行成功！"
echo "📂 所有结果已保存至: $OUTPUT_DIR"
echo "========================================"
