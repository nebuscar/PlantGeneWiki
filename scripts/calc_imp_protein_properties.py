#!/usr/bin/env python3
"""批量计算IMP蛋白序列的理化性质（等电点、分子量、氨基酸长度）"""

import os
import argparse
from Bio import SeqIO
from Bio.SeqUtils.ProtParam import ProteinAnalysis

STANDARD_AA = set("ACDEFGHIKLMNPQRSTVWY")


def calculate_properties(record):
    """计算单条蛋白序列的理化性质"""
    seq = str(record.seq).replace("*", "").strip()
    length = len(seq)

    if length == 0:
        return record.id, length, None, None

    # 过滤非标准氨基酸
    filtered = "".join(aa for aa in seq if aa in STANDARD_AA)
    if len(filtered) == 0:
        return record.id, length, None, None

    try:
        prot = ProteinAnalysis(filtered)
        pi = round(prot.isoelectric_point(), 2)
        mw = round(prot.molecular_weight(), 2)
    except Exception:
        return record.id, length, None, None

    return record.id, length, pi, mw


def process_species(sp_dir, output_dir):
    """处理单个物种目录"""
    sp_name = os.path.basename(sp_dir)

    # 查找蛋白文件
    faa_files = [f for f in os.listdir(sp_dir) if f.endswith(".prot.fasta")]
    if not faa_files:
        print(f"[WARN] {sp_name}: 未找到 .prot.fasta，跳过")
        return
    faa_path = os.path.join(sp_dir, faa_files[0])

    # 计算
    results = []
    for record in SeqIO.parse(faa_path, "fasta"):
        prot_id, length, pi, mw = calculate_properties(record)
        results.append([prot_id, length, pi, mw])

    # 输出
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"{sp_name}_protein_properties.tsv")

    with open(out_path, "w") as f:
        f.write("protein_id\tprotein_length\tisoelectric_point\tmolecular_weight\n")
        for row in results:
            f.write(f"{row[0]}\t{row[1]}\t{row[2]}\t{row[3]}\n")

    print(f"[OK] {sp_name}: {len(results)} 条记录 → {out_path}")


def main():
    parser = argparse.ArgumentParser(description="计算IMP蛋白理化性质")
    parser.add_argument("-i", "--input", default="/DATA/data2/downloads/IMP",
                        help="IMP数据根目录 (默认: /DATA/data2/downloads/IMP)")
    parser.add_argument("-o", "--output", default="./result/imp_pi_mw",
                        help="输出目录 (默认: ./result/imp_pi_mw)")
    args = parser.parse_args()

    if not os.path.isdir(args.input):
        print(f"[ERROR] 目录不存在: {args.input}")
        return

    os.makedirs(args.output, exist_ok=True)

    for name in sorted(os.listdir(args.input)):
        sp_path = os.path.join(args.input, name)
        if os.path.isdir(sp_path):
            sp_output = args.output
            process_species(sp_path, sp_output)

    print("[DONE]")


if __name__ == "__main__":
    main()
