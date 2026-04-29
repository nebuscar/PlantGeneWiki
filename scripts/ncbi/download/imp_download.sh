#!/bin/bash
#==============================================================================
# IMP 基因组数据批量下载脚本
# 从 https://www.bic.ac.cn/IMP 批量获取植物物种基因组数据
#==============================================================================

set -e

# 项目目录
PROJECT_DIR="/home/nizhu/Projects/plantsdb"
SCRIPTS_DIR="${PROJECT_DIR}/scripts/imp_crawler"
DOWNLOAD_DIR="${PROJECT_DIR}/downloads/IMP"
LOG_DIR=""

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

show_help() {
    cat <<EOF
IMP 基因组数据批量下载脚本

用法: $0 [选项]

选项:
  -h, --help              显示帮助
  -m, --manifest FILE     指定物种清单文件（TSV/JSON）
  -s, --species CODE      指定单个物种代码测试
  -l, --limit NUM         限制处理物种数量
  -d, --dry-run           仅显示，不实际下载
  -o, --outdir DIR        指定下载目录（默认: /DATA/data2/downloads/IMP）
  --list                  仅获取物种列表
  --no-skip               重新下载已存在的文件

示例:
  $0 --dry-run            # 预览要下载的内容
  $0 --species Apu1       # 测试下载单个物种
  $0 --limit 10           # 限制下载10个物种
  $0 --list               # 仅获取物种列表
  $0 -o /custom/path      # 指定自定义下载目录
EOF
}

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 参数解析
MANIFEST_FILE=""
SPECIES_CODE=""
LIMIT=""
DRY_RUN=""
NO_SKIP=""
LIST_ONLY="no"
OUTDIR=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help) show_help; exit 0 ;;
        -m|--manifest) MANIFEST_FILE="$2"; shift 2 ;;
        -s|--species) SPECIES_CODE="$2"; shift 2 ;;
        -l|--limit) LIMIT="--limit $2"; shift 2 ;;
        -d|--dry-run) DRY_RUN="--dry-run"; shift ;;
        -o|--outdir) OUTDIR="$2"; shift 2 ;;
        --no-skip) NO_SKIP="--no-skip"; shift ;;
        --list) LIST_ONLY="yes"; shift ;;
        *) log_error "未知选项: $1"; exit 1 ;;
    esac
done

# 设置默认下载目录
DOWNLOAD_DIR="${OUTDIR:-/DATA/data2/downloads/IMP}"
LOG_DIR="${DOWNLOAD_DIR}/logs"

mkdir -p "$DOWNLOAD_DIR" "$LOG_DIR"

echo "=============================================="
echo "IMP 基因组数据批量下载"
echo "=============================================="
echo "下载目录: $DOWNLOAD_DIR"

if [[ "$DRY_RUN" == "--dry-run" ]]; then
    log_warn "Dry Run 模式 - 仅显示，不实际下载"
fi

echo "----------------------------------------------"

# Step 1: 获取物种列表
if [[ "$LIST_ONLY" == "yes" ]]; then
    log_info "Step 1: 获取物种列表..."
    python3 "${SCRIPTS_DIR}/species_crawler.py"
    log_info "完成: ${DOWNLOAD_DIR}/species_manifest.tsv"
    exit 0
fi

# Step 2: 下载数据
log_info "Step 2: 下载基因组数据..."

if [[ -n "$SPECIES_CODE" ]]; then
    log_info "下载物种: $SPECIES_CODE"
    python3 "${SCRIPTS_DIR}/download_manager.py" \
        --species "$SPECIES_CODE" \
        --outdir "$DOWNLOAD_DIR" \
        --logdir "$LOG_DIR" \
        $DRY_RUN
elif [[ -n "$MANIFEST_FILE" ]]; then
    log_info "使用物种清单: $MANIFEST_FILE"
    python3 "${SCRIPTS_DIR}/download_manager.py" \
        --manifest "$MANIFEST_FILE" \
        --outdir "$DOWNLOAD_DIR" \
        --logdir "$LOG_DIR" \
        $LIMIT $DRY_RUN $NO_SKIP
else
    log_info "使用已存在的物种目录"
    python3 "${SCRIPTS_DIR}/download_manager.py" \
        --outdir "$DOWNLOAD_DIR" \
        --logdir "$LOG_DIR" \
        $LIMIT $DRY_RUN $NO_SKIP
fi

# Step 3: 生成报表
log_info "Step 3: 生成数据报表..."
python3 "${SCRIPTS_DIR}/excel_writer.py" \
    --indir "$DOWNLOAD_DIR" \
    --out "${DOWNLOAD_DIR}/IMP_data_inventory.xlsx"

echo "=============================================="
echo "全部完成!"
echo "=============================================="
echo ""
echo "输出:"
echo "  数据目录: $DOWNLOAD_DIR"
echo "  数据报表: ${DOWNLOAD_DIR}/IMP_data_inventory.xlsx"
echo "  日志目录: $LOG_DIR"
