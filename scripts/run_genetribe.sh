#!/bin/bash
set -eo pipefail

# 强制在项目根目录
cd "$(dirname "$0")/.."
echo "=== 工作目录：$PWD ==="

# ==================== 配置 ====================
SP1=Hopea_chinensis
SP2=Hopea_hainanensis
OUT_DIR="./genetribe_final"

# 自动找文件
PROT1=$(find sample/$SP1 -name "*protein*" | head -1)
PROT2=$(find sample/$SP2 -name "*protein*" | head -1)
BED1=$(find sample/$SP1 -name "*.bed" | head -1)
BED2=$(find sample/$SP2 -name "*.bed" | head -1)

mkdir -p "$OUT_DIR"
# ==============================================

# 复制文件到运行目录
cp -f "$PROT1" "$OUT_DIR/$SP1.fa"
cp -f "$PROT2" "$OUT_DIR/$SP2.fa"
cp -f "$BED1" "$OUT_DIR/$SP1.bed"
cp -f "$BED2" "$OUT_DIR/$SP2.bed"

# 进入运行目录
cd "$OUT_DIR"

# ==================== 旧版正确命令！====================
echo -e "\n🚀 运行 GeneTribe（旧版兼容）..."
genetribe core -l "$SP1" -f "$SP2"

echo -e "\n🎉 全部完成！"
echo -e "📄 同源基因结果在此："
ls -l *.RBH
