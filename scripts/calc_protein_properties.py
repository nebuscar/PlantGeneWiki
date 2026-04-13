#!/usr/bin/env python3
import os
import argparse
import pandas as pd
from Bio import SeqIO
from Bio.SeqUtils.ProtParam import ProteinAnalysis

STANDARD_AA = set("ACDEFGHIKLMNPQRSTVWY")


def calculate_protein_properties(seq_record):
    """计算单条蛋白序列的理化性质：长度、等电点、分子量"""
    seq = str(seq_record.seq).replace("*", "").strip()
    if len(seq) == 0:
        return seq_record.id, len(seq), None, None

    # 过滤非标准氨基酸，避免 ProteinAnalysis 抛异常
    filtered_seq = "".join(aa for aa in seq if aa in STANDARD_AA)
    if len(filtered_seq) == 0:
        return seq_record.id, len(seq), None, None

    try:
        prot_anal = ProteinAnalysis(filtered_seq)
        protein_length = len(seq)
        isoelectric_point = prot_anal.isoelectric_point()
        molecular_weight = prot_anal.molecular_weight()
    except ValueError as e:
        print(f"警告：序列 {seq_record.id} 计算失败 → {e}")
        return seq_record.id, len(seq), None, None

    return seq_record.id, protein_length, isoelectric_point, molecular_weight


def export_file(df, output_path, fmt):
    """导出文件：支持 csv/tsv/txt/xlsx"""
    if fmt == "csv":
        df.to_csv(output_path, index=False)
    elif fmt in ["tsv", "txt"]:
        df.to_csv(output_path, index=False, sep="\t")
    elif fmt == "xlsx":
        df.to_excel(output_path, index=False, engine="openpyxl")
    else:
        raise ValueError(f"不支持的输出格式：{fmt}")


def process_species(species_path, output_dir, output_fmt):
    """处理单个物种，并输出到指定位置"""
    species_name = os.path.basename(species_path)

    # 查找蛋白文件
    faa_files = [f for f in os.listdir(species_path) if f.endswith("_protein.faa")]
    if not faa_files:
        print(f"[WARN] {species_name}：未找到蛋白文件，跳过")
        return
    if len(faa_files) > 1:
        print(f"[WARN] {species_name}：找到多个蛋白文件 {faa_files}，使用 {faa_files[0]}")
    faa_file = os.path.join(species_path, faa_files[0])

    print(f"[OK] 处理中：{species_name}")

    # 计算
    results = []
    for record in SeqIO.parse(faa_file, "fasta"):
        prot_id, length, pi, mw = calculate_protein_properties(record)
        results.append(
            [
                prot_id,
                length,
                round(pi, 2) if pi is not None else None,
                round(mw, 2) if mw is not None else None,
            ]
        )

    df = pd.DataFrame(
        results,
        columns=[
            "Protein_ID",
            "Protein_Length",
            "Isoelectric_Point",
            "Molecular_Weight",
        ],
    )

    # 输出文件名
    filename = f"{species_name}_protein_properties.{output_fmt}"
    output_path = os.path.join(output_dir, filename)

    export_file(df, output_path, output_fmt)
    print(f"   已保存 → {output_path}\n")


def main():
    parser = argparse.ArgumentParser(
        description="蛋白理化性质计算（长度、等电点、分子量）",
        epilog="示例：\n  默认输出到各物种目录：python script.py -i ../sample -f csv\n  指定统一输出目录：python script.py -i ../sample -o ./output -f xlsx",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "-i", "--input", required=True, help="输入根目录（含多个物种文件夹）"
    )
    parser.add_argument(
        "-o", "--output", help="可选：指定统一输出目录（默认输出到各物种自己的文件夹）"
    )
    parser.add_argument(
        "-f",
        "--format",
        default="csv",
        choices=["csv", "tsv", "txt", "xlsx"],
        help="输出格式：csv(默认) tsv txt xlsx",
    )

    args = parser.parse_args()
    fmt = args.format

    # 检查输入目录
    if not os.path.isdir(args.input):
        print(f"[ERROR] 错误：输入目录不存在 {args.input}")
        return

    # 统一输出目录时提前创建
    if args.output:
        os.makedirs(args.output, exist_ok=True)

    # 遍历物种
    for name in os.listdir(args.input):
        sp_path = os.path.join(args.input, name)
        if not os.path.isdir(sp_path):
            continue

        # 输出目录逻辑：未指定则输出到物种自身目录
        out_dir = args.output if args.output else sp_path
        if not args.output:
            os.makedirs(out_dir, exist_ok=True)

        process_species(sp_path, out_dir, fmt)

    print("[DONE] 所有物种处理完成！")


if __name__ == "__main__":
    main()
