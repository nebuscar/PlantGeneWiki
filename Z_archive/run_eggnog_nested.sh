#!/bin/bash
# ============================================================
# 全自动运行 eggNOG-mapper（支持嵌套目录结构）
# 目录结构要求：
#   input_dir/                     （输入根目录，默认当前目录）
#     species_A/                   （子目录名作为物种名）
#       *.protein.faa              （必须以此结尾）
#     species_B/
#       *.protein.faa
#     ...
# 用法: ./run_eggnog_nested.sh [选项]
# ============================================================

# 显示帮助信息
show_help() {
    cat << EOF
用法: $0 [选项]

自动检索输入根目录下的每个子目录（一级子目录），查找以 .protein.faa 结尾的文件，
依次运行 eggNOG-mapper，并自动提取六列信息（protein_id, species, GO, KEGG, Pfam, function_description）。

选项:
  -d DIR         输入根目录（默认: 当前目录，即你运行脚本时所在的目录）
                 脚本会检索该目录下的每个一级子目录，将子目录名作为物种名。
  -o DIR         输出根目录（默认: 输入根目录/eggnog_output）
  -c CPU         使用的 CPU 核心数（默认: 30）
  -f FORMAT      输出格式: tsv, csv, xlsx（默认: tsv）
  -s SPECIES     手动指定物种名（覆盖自动从子目录名提取，通常不推荐）
  --override     强制覆盖已有输出文件（默认：覆盖）
  -h, --help     显示此帮助信息

说明:
  - 输入根目录下的每个一级子目录被视为一个物种。
  - 每个物种子目录内必须包含一个以 .protein.faa 结尾的文件，否则会被跳过。
  - 若存在多个 .protein.faa 文件，仅使用第一个并输出警告。
  - **若不指定 -d，脚本默认使用你运行脚本时所在的目录（即当前工作目录）作为输入根目录。**

示例:
  # 处理当前目录下的所有子目录（先 cd 到包含物种目录的父目录，再执行脚本）
  cd /path/to/your/species_parent_dir
  $0

  # 指定输入目录（无论你在哪个目录执行，都会处理 /data/genomes 下的子目录）
  $0 -d /data/genomes -c 30 -f csv

  # 指定输入和输出目录
  $0 -d /data/genomes -o /data/results

  # 查看帮助
  $0 -h
EOF
    exit 0
}

# ========== 默认参数（可修改） ==========
DATA_DIR="/DATA/data2/emapperdb-5.0.2"   # eggNOG数据库路径
CPU=30                                    # 默认CPU核心数
OUTPUT_FORMAT="tsv"                       # 默认输出格式
CONDA_ENV="biotools"                      # conda环境名
TAX_SCOPE="Eukaryota"                     # 分类范围
EVALUE="1e-5"                             # E-value阈值
TARGET_ORTHOLOGS="all"                    # 直系同源范围
INPUT_DIR="."                             # 默认输入根目录（当前目录）
OUTPUT_ROOT=""                            # 默认输出根目录（稍后设置）
MANUAL_SPECIES=""                         # 手动指定的物种名
OVERRIDE="--override"                     # 覆盖已有结果
# =======================================

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case "$1" in
        -d) INPUT_DIR="$2"; shift 2 ;;
        -o) OUTPUT_ROOT="$2"; shift 2 ;;
        -c) CPU="$2"; shift 2 ;;
        -f) OUTPUT_FORMAT="$2"; shift 2 ;;
        -s) MANUAL_SPECIES="$2"; shift 2 ;;
        --override) OVERRIDE="--override"; shift ;;
        -h|--help) show_help ;;
        *) echo "未知参数: $1"; show_help ;;
    esac
done

# 设置输出根目录
if [ -z "$OUTPUT_ROOT" ]; then
    OUTPUT_ROOT="${INPUT_DIR}/eggnog_output"
fi
mkdir -p "$OUTPUT_ROOT"

# 检查输入目录是否存在
if [ ! -d "$INPUT_DIR" ]; then
    echo "错误：输入目录 $INPUT_DIR 不存在"
    exit 1
fi

# 激活 conda 环境
if ! command -v conda &> /dev/null; then
    echo "错误：conda 未找到，请先初始化 conda"
    exit 1
fi
source $(conda info --base)/etc/profile.d/conda.sh
conda activate "$CONDA_ENV"
if [ $? -ne 0 ]; then
    echo "错误：无法激活 conda 环境 $CONDA_ENV"
    exit 1
fi

# 检查 emapper.py 是否可用
if ! command -v emapper.py &> /dev/null; then
    echo "错误：emapper.py 未找到，请确认 eggnog-mapper 已安装在 $CONDA_ENV 环境中"
    exit 1
fi

# 查找所有一级子目录
mapfile -t subdirs < <(find -L "$INPUT_DIR" -maxdepth 1 -mindepth 1 -type d | sort)
if [ ${#subdirs[@]} -eq 0 ]; then
    echo "错误：在目录 $INPUT_DIR 中没有找到子目录"
    exit 1
fi

echo "找到 ${#subdirs[@]} 个子目录："
printf '  %s\n' "${subdirs[@]}"

# 循环处理每个子目录
for species_dir in "${subdirs[@]}"; do
    # 物种名（子目录名）
    species_name=$(basename "$species_dir")
    echo "========================================"
    echo "处理物种: $species_name ($species_dir)"

    # 在子目录中查找以 _protein.faa 结尾的文件
    faa_files=()
    while IFS= read -r -d '' file; do
        faa_files+=("$file")
    done < <(find -L "$species_dir" -maxdepth 1 -name "*_protein.faa" -type f -print0)

    if [ ${#faa_files[@]} -eq 0 ]; then
        echo "[WARN] 物种 $species_name 的子目录中没有找到 _protein.faa 文件，跳过"
        continue
    fi

    if [ ${#faa_files[@]} -gt 1 ]; then
        echo "[WARN] 物种 $species_name 的子目录中找到多个 _protein.faa 文件，仅使用第一个: ${faa_files[0]}"
    fi

    faa="${faa_files[0]}"
    echo "使用文件: $faa"

    # 创建该物种的输出目录
    species_output_dir="${OUTPUT_ROOT}/${species_name}"
    mkdir -p "$species_output_dir"

    # 输出前缀（不含扩展名）
    base=$(basename "$faa" .protein.faa)
    prefix="${species_output_dir}/${base}"

    # 1. 运行 eggNOG-mapper
    echo "运行 emapper.py..."
    emapper.py -i "$faa" \
        -o "$prefix" \
        --data_dir "$DATA_DIR" \
        --cpu "$CPU" \
        -m diamond \
        --tax_scope "$TAX_SCOPE" \
        --evalue "$EVALUE" \
        --target_orthologs "$TARGET_ORTHOLOGS" \
        $OVERRIDE

    annot_file="${prefix}.emapper.annotations"
    if [ ! -f "$annot_file" ]; then
        echo "错误：注释文件未生成，请检查 $faa 的运行日志"
        continue
    fi

    # 2. 提取六列信息
    if [ -n "$MANUAL_SPECIES" ]; then
        species="$MANUAL_SPECIES"
    else
        species="$species_name"
    fi
    output_file="${prefix}.extracted.${OUTPUT_FORMAT}"

    echo "提取注释信息到: $output_file"

    # 内嵌 Python 提取脚本
    python3 <<PYTHON_SCRIPT
import csv, sys, os
infile = "$annot_file"
outfile = "$output_file"
species = "$species"
fmt = "$OUTPUT_FORMAT"

def get_indices(header):
    cols = header.strip().split('\t')
    # 如果第一列以 # 开头，去掉 #
    if cols[0].startswith('#'):
        cols[0] = cols[0][1:]
    expected = ["query", "Description", "GOs", "KEGG_ko", "PFAMs"]
    indices = {}
    for e in expected:
        try:
            indices[e] = cols.index(e)
        except ValueError:
            sys.stderr.write(f"列 {e} 未找到\n")
            sys.exit(1)
    return indices

with open(infile) as f:
    header_line = None
    for line in f:
        if line.startswith("#query"):
            header_line = line
            break
    if not header_line:
        sys.stderr.write("未找到表头\n")
        sys.exit(1)
    idx = get_indices(header_line)
    rows = []
    for line in f:
        if line.startswith("#") or not line.strip():
            continue
        fields = line.strip().split('\t')
        if len(fields) <= max(idx.values()):
            continue
        pid = fields[idx["query"]]
        go = fields[idx["GOs"]] if fields[idx["GOs"]] != "-" else ""
        kegg = fields[idx["KEGG_ko"]] if fields[idx["KEGG_ko"]] != "-" else ""
        pfam = fields[idx["PFAMs"]] if fields[idx["PFAMs"]] != "-" else ""
        desc = fields[idx["Description"]] if fields[idx["Description"]] != "-" else ""
        rows.append([pid, species, go, kegg, pfam, desc])

if fmt == "tsv":
    with open(outfile, 'w', newline='') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerow(["protein_id", "species", "GO", "KEGG", "Pfam", "function_description"])
        w.writerows(rows)
elif fmt == "csv":
    with open(outfile, 'w', newline='') as f:
        w = csv.writer(f, delimiter=',')
        w.writerow(["protein_id", "species", "GO", "KEGG", "Pfam", "function_description"])
        w.writerows(rows)
elif fmt == "xlsx":
    try:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Annotations"
        ws.append(["protein_id", "species", "GO", "KEGG", "Pfam", "function_description"])
        for row in rows:
            ws.append(row)
        wb.save(outfile)
    except ImportError:
        sys.stderr.write("需要安装 openpyxl: pip install openpyxl\n")
        sys.exit(1)
else:
    sys.stderr.write(f"不支持的格式: {fmt}\n")
    sys.exit(1)
print(f"提取完成: {outfile}")
PYTHON_SCRIPT

    echo "完成处理: $species_name -> $output_file"
done

echo "========================================"
echo "所有任务完成！"