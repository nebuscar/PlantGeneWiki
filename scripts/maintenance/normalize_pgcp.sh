#!/usr/bin/env bash
#===============================================
# PGCP 数据描述行标准化脚本
# 功能：将 PGCP 原始 gz 文件转换为标准描述行格式
# 格式：{原始ID} {物种名}|{类型}
#===============================================

set -euo pipefail

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

show_help() {
    cat <<EOF
PGCP 数据描述行标准化脚本
========================================

用法：$(basename "$0") [选项] <输入文件>

选项：
    -i, --input DIR       输入目录（批量处理）
    -o, --output DIR      输出目录（默认：原目录覆盖）
    -s, --species NAME    强制指定物种名（覆盖文件名推断）
    -n, --dry-run         模拟运行，不实际修改
    -v, --verbose        显示详细信息
    --help               显示帮助

示例：
    # 批量处理目录
    $(basename "$0") -i /DATA/downloads/PGCP -o ./standardized

    # 处理单个文件
    $(basename "$0") abies_alba.cds.fa.gz

    # 模拟运行
    $(basename "$0") -n -i ./PGCP
========================================
EOF
}

log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# 从文件名推断类型
infer_type() {
    local filename="$1"
    case "$filename" in
        *.pep.fa.gz|*.protein.fa.gz)
            echo "Peptide"
            ;;
        *.cds.fa.gz)
            echo "CDS"
            ;;
        *.genomic.fa.gz)
            echo "genomic"
            ;;
        *.gene.fa.gz)
            echo "Gene"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

# 从文件名推断物种名
infer_species() {
    local filename="$1"
    # 文件名格式：species_name.type.fa.gz
    local basename=$(basename "$filename" .fa.gz)
    # 去掉类型后缀
    local species="${basename%.cds}"
    species="${species%.pep}"
    species="${species%.protein}"
    species="${species%.genomic}"
    species="${species%.gene}"
    echo "$species"
}

# 标准化单个文件
process_file() {
    local input_file="$1"
    local output_dir="${2:-}"
    local forced_species="${3:-}"
    local dry_run="${4:-false}"
    local verbose="${5:-false}"

    local filename=$(basename "$input_file")
    local type=$(infer_type "$filename")
    local species="${forced_species:-$(infer_species "$filename")}"

    if [[ "$type" == "unknown" ]]; then
        log_warn "跳过未知类型: $filename"
        return 1
    fi

    # 确定输出文件
    local output_file
    if [[ -n "$output_dir" ]]; then
        [[ -d "$output_dir" ]] || mkdir -p "$output_dir"
        output_file="$output_dir/$filename"
    else
        output_file="$input_file"
    fi

    if [[ "$dry_run" == "true" ]]; then
        log_info "[DRY-RUN] $filename → species=$species type=$type"
        return 0
    fi

    if [[ "$verbose" == "true" ]]; then
        log_info "处理: $filename → species=$species type=$type"
    fi

    # 创建临时文件
    local temp_file=$(mktemp)

    # 解压、处理、重压缩
    if zcat "$input_file" 2>/dev/null | \
        awk -v species="$species" -v type="$type" '
        BEGIN { FS=" "; OFS=" " }
        /^>/ {
            # 提取原始ID（第一列，去掉>）
            n = split(substr($0,2), parts, " ");
            original_id = parts[1];
            # 重新格式化描述行
            print ">" original_id, species "|" type
        }
        /^[^>]/ {
            print
        }
        ' > "$temp_file"; then
        # 替换原文件或输出到目标目录
        if [[ "$output_file" != "$input_file" ]]; then
            pigz -c "$temp_file" > "$output_file"
        else
            pigz -c "$temp_file" > "${temp_file}.gz"
            mv "${temp_file}.gz" "$input_file"
        fi
        rm -f "$temp_file"
        [[ "$verbose" == "true" ]] && log_info "完成: $filename"
    else
        log_error "处理失败: $filename"
        rm -f "$temp_file"
        return 1
    fi
}

# 批量处理目录
process_directory() {
    local input_dir="$1"
    local output_dir="${2:-}"
    local forced_species="${3:-}"
    local dry_run="${4:-false}"
    local verbose="${5:-false}"

    local count=0
    local total=$(find "$input_dir" -name "*.fa.gz" -o -name "*.fasta.gz" 2>/dev/null | wc -l)
    log_info "找到 $total 个 gz 文件"

    while IFS= read -r file; do
        ((count++))
        echo -ne "\r进度: $count/$total"
        process_file "$file" "$output_dir" "$forced_species" "$dry_run" "$verbose" || true
    done < <(find "$input_dir" \( -name "*.fa.gz" -o -name "*.fasta.gz" \) -type f 2>/dev/null)
    echo ""
}

# 主程序
main() {
    local input_path=""
    local output_dir=""
    local forced_species=""
    local dry_run=false
    local verbose=false

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                show_help
                exit 0
                ;;
            -i|--input)
                input_path="$2"
                shift 2
                ;;
            -o|--output)
                output_dir="$2"
                shift 2
                ;;
            -s|--species)
                forced_species="$2"
                shift 2
                ;;
            -n|--dry-run)
                dry_run=true
                shift
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            -*)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
            *)
                input_path="$1"
                shift
                ;;
        esac
    done

    if [[ -z "$input_path" ]]; then
        log_error "请指定输入文件或目录"
        show_help
        exit 1
    fi

    log_info "PGCP 数据标准化工具"
    log_info "========================================"

    if [[ -d "$input_path" ]]; then
        process_directory "$input_path" "$output_dir" "$forced_species" "$dry_run" "$verbose"
    elif [[ -f "$input_path" ]]; then
        process_file "$input_path" "$output_dir" "$forced_species" "$dry_run" "$verbose"
    else
        log_error "路径不存在: $input_path"
        exit 1
    fi

    log_info "完成！"
}

main "$@"