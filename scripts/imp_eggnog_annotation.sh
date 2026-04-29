#!/bin/bash
# eggNOG-mapper 功能注释分析脚本
# 读取 IMP 目录下物种数据，逐个进行 eggNOG-mapper 分析，输出 xlsx 表格

set -e

# 配置
IMP_DIR="/DATA/data2/downloads/IMP"
SCRIPT_DIR="/home/nizhu/Projects/plantsdb/scripts"
PROJECT_DIR="/home/nizhu/Projects/plantsdb"
DATA_DIR="${PROJECT_DIR}/data/imp_eggnog"
RESULT_DIR="${PROJECT_DIR}/result/imp_eggnog"

# eggNOG-mapper 配置
EMAPPER="/home/nizhu/.local/bin/emapper.py"
EMAPPER_DB="/DATA/data2/emapperdb-5.0.2"

# 运行节点配置
REMOTE_NODE="gpu-node2"
REMOTE_CPU=60
CONDA_ENV="biotools"

# 创建目录
mkdir -p "${DATA_DIR}" "${RESULT_DIR}"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 检查依赖
check_dependencies() {
    if [[ ! -f "${EMAPPER}" ]]; then
        log "错误: eggNOG-mapper 未找到: ${EMAPPER}"
        exit 1
    fi

    if ! command -v python3 &>/dev/null; then
        log "错误: python3 未找到"
        exit 1
    fi

    if ! python3 -c "import pandas" 2>/dev/null; then
        log "错误: pandas 未安装，请运行: pip install pandas openpyxl"
        exit 1
    fi
}

# 获取物种列表
get_species_list() {
    local imp_dir=$1
    # 获取所有包含 .prot.fasta 文件的物种目录
    find "${imp_dir}" -maxdepth 1 -type d | while read -r dir; do
        local species=$(basename "${dir}")
        local prot_file="${dir}/${species}.prot.fasta"
        # 处理物种名中有下划线对应多个可能的文件
        if ls "${dir}"/*.prot.fasta 1>/dev/null 2>&1; then
            echo "${dir}"
        fi
    done
}

# 获取物种对应的蛋白质文件
get_protein_file() {
    local species_dir=$1
    local species_name=$(basename "${species_dir}")

    # 尝试精确匹配
    if [[ -f "${species_dir}/${species_name}.prot.fasta" ]]; then
        echo "${species_dir}/${species_name}.prot.fasta"
        return 0
    fi

    # 尝试通配符匹配
    local prot_file=$(ls "${species_dir}"/*.prot.fasta 2>/dev/null | head -1)
    if [[ -n "${prot_file}" ]]; then
        echo "${prot_file}"
        return 0
    fi

    return 1
}

# 运行 eggNOG-mapper
run_eggnog() {
    local input_file=$1
    local output_base=$2
    local species_name=$3

    log "开始分析物种: ${species_name}"

    # 创建该物种的临时工作目录
    local work_dir="${DATA_DIR}/${species_name}"
    mkdir -p "${work_dir}"

    # 完整注释文件路径
    local full_annot_file="${work_dir}/${output_base}.emapper.full_annotations"

    # 如果完整注释已存在，直接返回
    if [[ -f "${full_annot_file}" ]]; then
        log "  完整注释已存在: ${full_annot_file}"
        echo "${full_annot_file}"
        return 0
    fi

    # 运行 eggNOG-mapper 生成完整注释
    log "  在 ${REMOTE_NODE} 上运行 eggNOG-mapper (${REMOTE_CPU} 核)..."
    ssh "${REMOTE_NODE}" \
        "cd '${work_dir}' && \
        source /home/nizhu/software/miniforge3/etc/profile.d/conda.sh && \
        conda activate ${CONDA_ENV} && \
        python3 '${EMAPPER}' \
            -i '${input_file}' \
            -o '${output_base}' \
            --data_dir '${EMAPPER_DB}' \
            -m diamond \
            --cpu ${REMOTE_CPU} \
            --no_file_comment"

    # 等待文件生成
    local count=0
    while [[ ! -f "${work_dir}/${output_base}.emapper.annotations" && $count -lt 60 ]]; do
        sleep 5
        count=$((count + 1))
    done

    # 移动注释文件到目标位置
    if [[ -f "${work_dir}/${output_base}.emapper.annotations" ]]; then
        mv "${work_dir}/${output_base}.emapper.annotations" "${full_annot_file}"
        log "  注释文件已生成: ${full_annot_file}"
    else
        log "  警告: 注释文件未生成"
    fi

    echo "${full_annot_file}"
}

# 解析 eggNOG 注释结果并生成 xlsx
parse_and_generate_xlsx() {
    local annot_file=$1
    local species_name=$2

    if [[ ! -f "${annot_file}" ]]; then
        log "  注释文件不存在: ${annot_file}"
        return 1
    fi

    log "  解析注释结果: ${annot_file}"

    # Python 脚本解析并生成 xlsx
    python3 << EOF
import pandas as pd
import sys
import re

annot_file = "${annot_file}"
species_name = "${species_name}"
output_xlsx = "${RESULT_DIR}/${species_name}.eggnog_annotation.xlsx"

# 读取注释文件
# eggNOG-mapper 输出格式: query, seed_ortholog, evalue, score, predicted_name,goterms, KEGG, PFAMs, eggNOG OGs, best_tax_level, Description, COG functional categories, CAzyme

data = []
with open(annot_file, 'r') as f:
    for line in f:
        if line.startswith('#') or line.startswith('query'):
            continue
        line = line.strip()
        if not line:
            continue
        fields = line.split('\t')
        if len(fields) < 12:
            continue

        query = fields[0]
        # eggNOG-mapper 注释文件列顺序：
        # 0:query, 1:seed_ortholog, 2:evalue, 3:score, 4:eggNOG_OGs, 5:taxon,
        # 6:KOG_category, 7:predicted_name, 8:@, 9:GO_terms, 10:EC, 11:KEGG_ko, 12:KEGG_pathway, 13:@, 14:CAzyme, 15:@, 16:@, 17:@, 18:@, 19:@, 20:PFAMs
        go_terms = fields[9] if len(fields) > 9 else ''
        kegg = fields[12] if len(fields) > 12 else ''
        pfam = fields[20] if len(fields) > 20 else ''
        description = fields[7] if len(fields) > 7 else ''

        # 清理 GO terms 格式 (去除 @... 后缀)
        go_terms_clean = re.sub(r'@.*', '', go_terms)

        # 清理 KEGG 格式
        kegg_clean = re.sub(r'@.*', '', kegg)

        data.append({
            'Gene_ID': query,
            'GO': go_terms_clean,
            'KEGG': kegg_clean,
            'Pfam': pfam,
            'Function_Description': description
        })

if data:
    df = pd.DataFrame(data)

    # 保留原始顺序，按基因 ID 排序
    df = df.sort_values('Gene_ID')

    # 生成 xlsx
    with pd.ExcelWriter(output_xlsx, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='eggnog_annotation', index=False)

        # 格式化工作表
        worksheet = writer.sheets['eggnog_annotation']
        for idx, col in enumerate(df.columns):
            max_width = max(
                len(str(col)),
                df[col].astype(str).str.len().max()
            )
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_width + 2, 50)

    print(f"生成了 {len(data)} 条记录")
    print(f"结果保存到: {output_xlsx}")
else:
    print("警告: 没有解析到任何注释数据")
    sys.exit(1)
EOF

    log "  xlsx 生成完成: ${RESULT_DIR}/${species_name}.eggnog_annotation.xlsx"
}

# 主流程
main() {
    log "========== eggNOG-mapper 功能注释分析 =========="
    log "IMP 目录: ${IMP_DIR}"
    log "中间数据目录: ${DATA_DIR}"
    log "结果输出目录: ${RESULT_DIR}"

    check_dependencies

    # 获取所有物种目录
    local species_dirs=$(find "${IMP_DIR}" -maxdepth 1 -type d | sort)
    local species_count=0

    for species_dir in ${species_dirs}; do
        [[ "${species_dir}" == "${IMP_DIR}" ]] && continue

        species_name=$(basename "${species_dir}")
        species_count=$((species_count + 1))

        log ""
        log "========== [${species_count}] 处理物种: ${species_name} =========="

        # 获取蛋白质文件
        local prot_file=$(get_protein_file "${species_dir}")
        if [[ -z "${prot_file}" ]]; then
            log "  跳过: 未找到蛋白质文件"
            continue
        fi

        log "  蛋白质文件: ${prot_file}"

        # 确定输出基础名 (从蛋白质文件名提取前缀)
        local prefix=$(basename "${prot_file}" .prot.fasta)
        local output_base="${species_name}.${prefix}"

        # 运行 eggNOG-mapper
        local annot_file=$(run_eggnog "${prot_file}" "${output_base}" "${species_name}")

        # 生成 xlsx
        if [[ -f "${annot_file}" ]]; then
            parse_and_generate_xlsx "${annot_file}" "${species_name}"
        else
            log "  警告: 注释文件未生成: ${annot_file}"
        fi
    done

    log ""
    log "========== 分析完成 =========="
    log "共处理 ${species_count} 个物种"
    log "结果保存在: ${RESULT_DIR}"
}

# 单独处理某个物种的函数
process_single_species() {
    local species_name=$1

    log "========== 单独处理物种: ${species_name} =========="

    local species_dir="${IMP_DIR}/${species_name}"
    if [[ ! -d "${species_dir}" ]]; then
        log "错误: 物种目录不存在: ${species_dir}"
        exit 1
    fi

    local prot_file=$(get_protein_file "${species_dir}")
    if [[ -z "${prot_file}" ]]; then
        log "错误: 未找到蛋白质文件"
        exit 1
    fi

    log "蛋白质文件: ${prot_file}"

    local prefix=$(basename "${prot_file}" .prot.fasta)
    local output_base="${species_name}.${prefix}"

    local annot_file=$(run_eggnog "${prot_file}" "${output_base}" "${species_name}")

    if [[ -f "${annot_file}" ]]; then
        parse_and_generate_xlsx "${annot_file}" "${species_name}"
    fi
}

# 显示帮助
show_help() {
    cat << EOF
用法: $0 [选项] [物种名]

选项:
    -h, --help          显示帮助信息
    -l, --list          列出所有可用物种
    -s, --species NAME  指定要处理的物种名

示例:
    $0                  # 处理所有物种
    $0 Acer_campestre   # 只处理 Acer_campestre
    $0 --list           # 列出所有物种
EOF
}

# 列出物种
list_species() {
    log "可用物种列表:"
    find "${IMP_DIR}" -maxdepth 1 -type d | sort | while read -r dir; do
        [[ "${dir}" == "${IMP_DIR}" ]] && continue
        species_name=$(basename "${dir}")
        prot_file=$(get_protein_file "${dir}" 2>/dev/null)
        if [[ -n "${prot_file}" ]]; then
            echo "  - ${species_name}"
        fi
    done
}

# 命令行参数处理
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    -l|--list)
        list_species
        exit 0
        ;;
    -s|--species)
        if [[ -z "${2:-}" ]]; then
            log "错误: 请指定物种名"
            show_help
            exit 1
        fi
        process_single_species "${2}"
        ;;
    *)
        if [[ -n "${1:-}" ]]; then
            process_single_species "${1}"
        else
            main
        fi
        ;;
esac
