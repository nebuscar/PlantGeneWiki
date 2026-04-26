#!/usr/bin/env python3
from pathlib import Path
import argparse
import pandas as pd  # 用于输出 xlsx/csv/tsv/txt（自动处理格式）

# ===================== 命令行参数配置 =====================
parser = argparse.ArgumentParser(
    description="GFF 基因ID与蛋白ID映射表生成工具:按 ; 分段解析，输出到物种文件夹",
    formatter_class=argparse.RawTextHelpFormatter,
    epilog="使用示例：\n"
    "  python 脚本.py -i /your/genome/path -f xlsx\n"
    "  python 脚本.py --input /your/genome/path --format csv\n"
    "  python 脚本.py -h  (查看帮助)",
)

# 输入路径
parser.add_argument(
    "-i",
    "--input",
    type=str,
    default="/home/nizhu/renjinran/downloads2/genomes",
    help="指定基因组根目录（包含各物种子文件夹）\n默认路径:/home/nizhu/renjinran/downloads2/genomes",
)

# 输出格式参数（新增！）
parser.add_argument(
    "-f",
    "--format",
    choices=["xlsx", "csv", "tsv", "txt"],
    default="xlsx",
    help="输出文件格式(可选:xlsx, csv, tsv, txt)\n默认:tsv",
)

# 解析参数
args = parser.parse_args()
ROOT_DIR = Path(args.input)
OUT_FORMAT = args.format.lower()

# ===================== 核心处理逻辑 =====================
for species_dir in ROOT_DIR.iterdir():
    if not species_dir.is_dir():
        continue

    print(f"\n正在处理物种:{species_dir.name}")
    mapping = {}

    # 查找该物种下所有 GFF 文件
    gff_files = list(species_dir.glob("*.gff")) + list(species_dir.glob("*.gff3"))
    if not gff_files:
        print("⚠️  无 GFF 文件，跳过")
        continue

    # 逐行解析
    for gff in gff_files:
        try:
            with open(gff, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    parts = line.split("\t")
                    if len(parts) < 9:
                        continue

                    # 只处理 CDS 行
                    if parts[2] not in ("CDS", "cds"):
                        continue

                    # 按 ; 分段解析
                    attr_str = parts[8]
                    attrs = {}
                    for seg in attr_str.split(";"):
                        seg = seg.strip()
                        if "=" not in seg:
                            continue
                        k, v = seg.split("=", 1)
                        attrs[k.strip()] = v.strip()

                    locus_tag = attrs.get("locus_tag")
                    protein_id = attrs.get("protein_id")

                    if locus_tag and protein_id:
                        mapping[locus_tag] = protein_id

        except Exception:
            print(f"⚠️  文件读取异常：{gff.name}")

    # 空结果不生成文件
    if not mapping:
        print("⚠️  未提取到有效映射，不生成文件")
        continue

    # 构建输出 DataFrame
    df = pd.DataFrame(sorted(mapping.items()), columns=["gene_id", "protein_id"])
    out_file = species_dir / f"{species_dir.name}_geneid_protid_mapping.{OUT_FORMAT}"

    # 按格式输出
    if OUT_FORMAT == "xlsx":
        df.to_excel(out_file, index=False)
    elif OUT_FORMAT == "csv":
        df.to_csv(out_file, index=False, encoding="utf-8-sig")
    elif OUT_FORMAT in ("tsv", "txt"):
        df.to_csv(out_file, index=False, encoding="utf-8", sep="\t")

    print(f"✅ 完成！输出：{out_file}")
    print(f"📊 有效映射数：{len(mapping)}")

print("\n🎉 所有物种处理完成！")
