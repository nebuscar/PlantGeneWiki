#!/usr/bin/env python3
"""
PGCP 引物设计脚本
使用 Primer3 (primer3_core) 为 CDS 或基因组序列设计引物

用法:
    python3 primer_design.py --input file.fa --type cds --output results/
    python3 primer_design.py --input file.fa --type genomic --output results/
    python3 primer_design.py --input file.fa --type cds --target 100-500 --output results/
"""

import os
import re
import sys
import gzip
import argparse
import subprocess
from pathlib import Path
from collections import defaultdict


class Primer3Runner:
    """Primer3 引物设计"""

    def __init__(self, primer3_path="primer3_core"):
        self.primer3_path = primer3_path
        self.default_params = {
            "PRIMER_TASK": "generic",
            "PRIMER_PICK_LEFT_PRIMER": 3,
            "PRIMER_PICK_RIGHT_PRIMER": 3,
            "PRIMER_PICK_INTERNAL_OLIGO": 0,
            "PRIMER_MIN_SIZE": 18,
            "PRIMER_OPT_SIZE": 20,
            "PRIMER_MAX_SIZE": 25,
            "PRIMER_MIN_TM": 55.0,
            "PRIMER_OPT_TM": 60.0,
            "PRIMER_MAX_TM": 65.0,
            "PRIMER_MIN_GC": 40.0,
            "PRIMER_MAX_GC": 60.0,
            "PRIMER_MAX_POLY_X": 4,
            "PRIMER_SELF_ANY": 8.0,
            "PRIMER_SELF_END": 3.0,
            "PRIMER_NUM_NS_ACCEPTED": 0,
            "PRIMER_MAX_NS": 0,
            "PRIMER_MAX_HYBRIDIZATION_TEMP": 65.0,
            "PRIMER_DNA_CONC": 50.0,
            "PRIMER_SALT_CONC": 50.0,
            "PRIMER_SALT_CORRECTIONS": 1,
            "PRIMER_SALT_DIVALENT": 2.0,
            "PRIMER_DNTP_CONC": 0.6,
            "PRIMER_MAX_SELF_ANY_TH": 47.0,
            "PRIMER_MAX_SELF_END_TH": 47.0,
            "PRIMER_PAIR_MAX_COMPL_ANY": 8.0,
            "PRIMER_PAIR_MAX_COMPL_END": 3.0,
            "PRIMER_PRODUCT_SIZE_RANGE": "70-250",
        }

    def read_fasta(self, fasta_file: Path) -> dict:
        """读取 FASTA 文件"""
        sequences = {}
        current_id = None
        current_seq = []

        opener = gzip.open if str(fasta_file).endswith('.gz') else open

        with opener(fasta_file, 'rt') as f:
            for line in f:
                line = line.strip()
                if line.startswith('>'):
                    if current_id:
                        sequences[current_id] = ''.join(current_seq)
                    current_id = line[1:].split()[0]  # 取第一个word作为ID
                    current_seq = []
                else:
                    current_seq.append(line.upper())

        if current_id:
            sequences[current_id] = ''.join(current_seq)

        return sequences

    def run_primer3(self, seq_id: str, sequence: str, params: dict = None) -> dict:
        """运行 Primer3 设计引物"""
        if params is None:
            params = self.default_params.copy()

        # 验证和修正参数
        params = self._validate_params(params)

        # 添加序列
        params["SEQUENCE_ID"] = seq_id
        params["SEQUENCE_TEMPLATE"] = sequence

        # 构建输入
        input_data = []
        for key, value in params.items():
            if key.startswith("SEQUENCE_"):
                input_data.append(f"{key}={value}")
            elif key.startswith("PRIMER_"):
                input_data.append(f"{key}={value}")

        input_str = "\n".join(input_data) + "\n=\n"

        # 运行 Primer3
        try:
            result = subprocess.run(
                [self.primer3_path],
                input=input_str,
                capture_output=True,
                text=True,
                timeout=30
            )
            output = result.stdout
        except Exception as e:
            return {"error": str(e), "primers": []}

        # 解析输出
        return self.parse_primer3_output(output)

    def parse_primer3_output(self, output: str) -> dict:
        """解析 Primer3 输出"""
        result = {
            "primers": [],
            "warnings": [],
            "stats": {}
        }

        current_primer = None

        for line in output.strip().split('\n'):
            if '=' not in line:
                continue

            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()

            # 引物对信息
            if key.startswith('PRIMER_PAIR_NUM_RETURNED'):
                result["pair_count"] = int(value)
            elif key == 'SEQUENCE_ID':
                result["seq_id"] = value
            elif key.startswith('PRIMER_LEFT_') and key.endswith('_SEQUENCE'):
                if current_primer is None:
                    current_primer = {}
                current_primer["left_seq"] = value
            elif key.startswith('PRIMER_RIGHT_') and key.endswith('_SEQUENCE'):
                if current_primer is None:
                    current_primer = {}
                current_primer["right_seq"] = value
            elif key.startswith('PRIMER_LEFT_') and '_TM' in key:
                if current_primer is None:
                    current_primer = {}
                current_primer["left_tm"] = float(value)
            elif key.startswith('PRIMER_RIGHT_') and '_TM' in key:
                if current_primer is None:
                    current_primer = {}
                current_primer["right_tm"] = float(value)
            elif key.startswith('PRIMER_LEFT_') and '_GC' in key:
                if current_primer is None:
                    current_primer = {}
                current_primer["left_gc"] = float(value)
            elif key.startswith('PRIMER_RIGHT_') and '_GC' in key:
                if current_primer is None:
                    current_primer = {}
                current_primer["right_gc"] = float(value)
            elif key.startswith('PRIMER_') and 'PRODUCT_SIZE' in key:
                if current_primer is not None:
                    current_primer["product_size"] = int(value)
                    result["primers"].append(current_primer)
                    current_primer = None
            elif key.startswith('PRIMER_WARNING'):
                result["warnings"].append(value)
            elif key.startswith('PRIMER_INTERNAL_') or key.startswith('SEQUENCE_'):
                continue
            elif key.startswith('PRIMER_') and key.endswith('_PENALTY'):
                if current_primer is not None:
                    current_primer["penalty"] = float(value)
            elif key.startswith('PRIMER_') and '_POS' in key:
                if current_primer is not None:
                    pos_key = 'left_pos' if 'LEFT' in key else 'right_pos'
                    current_primer[pos_key] = int(value)

        # 如果有未完成的引物
        if current_primer is not None and "product_size" in current_primer:
            result["primers"].append(current_primer)

        return result

    def _validate_params(self, params: dict) -> dict:
        """验证和修正 Primer3 参数"""
        params = params.copy()

        # SEQUENCE_TARGET: primer3 要求逗号分隔的位置对 (如 "100,400")
        # 如果格式不对 (如 "100-500" 或 "100 500")，直接删除让 primer3 自动选择
        if 'SEQUENCE_TARGET' in params:
            target = str(params['SEQUENCE_TARGET']).strip()
            if '-' in target or ' ' in target:
                # 格式不正确，删除该参数让 primer3 自动选择目标区域
                del params['SEQUENCE_TARGET']

        return params

    def design_primers_for_sequences(self, sequences: dict, output_file: Path, params: dict = None):
        """为多个序列设计引物"""
        all_results = []

        for seq_id, sequence in sequences.items():
            if len(sequence) < 100:
                all_results.append({
                    "seq_id": seq_id,
                    "length": len(sequence),
                    "status": "too_short",
                    "error": "序列长度 < 100bp"
                })
                continue

            result = self.run_primer3(seq_id, sequence, params)

            if "error" in result:
                all_results.append({
                    "seq_id": seq_id,
                    "length": len(sequence),
                    "status": "error",
                    "error": result["error"]
                })
            else:
                all_results.append({
                    "seq_id": seq_id,
                    "length": len(sequence),
                    "status": "success",
                    "pair_count": result.get("pair_count", 0),
                    "primers": result.get("primers", [])
                })

        # 保存结果
        self.save_results(all_results, output_file)

        return all_results

    def save_results(self, results: list, output_file: Path):
        """保存结果到文件"""
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            # 写入汇总
            f.write("# Primer Design Results\n")
            f.write(f"# Generated by PGCP Primer Design Pipeline\n")
            f.write("#\n")

            for r in results:
                f.write(f"\n{'='*60}\n")
                f.write(f"Seq ID: {r['seq_id']}\n")
                f.write(f"Length: {r['length']} bp\n")
                f.write(f"Status: {r['status']}\n")

                if r['status'] == 'success':
                    f.write(f"Primer Pairs Found: {r.get('pair_count', 0)}\n")

                    for i, p in enumerate(r['primers'], 1):
                        f.write(f"\n  --- Primer Pair {i} ---\n")
                        f.write(f"  Left Primer:  {p.get('left_seq', 'N/A')} "
                               f"(TM={p.get('left_tm', 0):.2f}°C, GC={p.get('left_gc', 0):.1f}%)\n")
                        f.write(f"  Right Primer: {p.get('right_seq', 'N/A')} "
                               f"(TM={p.get('right_tm', 0):.2f}°C, GC={p.get('right_gc', 0):.1f}%)\n")
                        f.write(f"  Product Size: {p.get('product_size', 0)} bp\n")
                        if 'penalty' in p:
                            f.write(f"  Penalty: {p['penalty']:.4f}\n")
                else:
                    f.write(f"Error: {r.get('error', 'Unknown error')}\n")

        # 同时保存 TSV 格式（仅成功的引物对）
        tsv_file = output_file.with_suffix('.tsv')
        with open(tsv_file, 'w') as f:
            f.write("Seq_ID\tSeq_Length\tPair#\tLeft_Primer\tLeft_TM\tLeft_GC\tLeft_Pos\tRight_Primer\tRight_TM\tRight_GC\tRight_Pos\tProduct_Size\tPenalty\n")
            for r in results:
                if r['status'] != 'success':
                    continue
                for i, p in enumerate(r['primers'], 1):
                    f.write(f"{r['seq_id']}\t{r['length']}\t{i}\t"
                           f"{p.get('left_seq', 'N/A')}\t{p.get('left_tm', 0):.2f}\t{p.get('left_gc', 0):.1f}\t{p.get('left_pos', 'N/A')}\t"
                           f"{p.get('right_seq', 'N/A')}\t{p.get('right_tm', 0):.2f}\t{p.get('right_gc', 0):.1f}\t{p.get('right_pos', 'N/A')}\t"
                           f"{p.get('product_size', 0)}\t{p.get('penalty', 'N/A')}\n")


def main():
    parser = argparse.ArgumentParser(
        description="PGCP 引物设计 - 使用 Primer3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 设计 CDS 引物
  python3 primer_design.py -i gene.cds.fa.gz -t cds -o results/

  # 设计基因组引物
  python3 primer_design.py -i gene.genomic.fa.gz -t genomic -o results/

  # 自定义参数
  python3 primer_design.py -i gene.cds.fa.gz -t cds -o results/ \\
      --min-tm 57 --max-tm 63 --product-size 150-300
"""
    )
    parser.add_argument("-i", "--input", required=True, help="输入 FASTA 文件")
    parser.add_argument("-t", "--type", choices=["cds", "genomic"], default="cds",
                       help="序列类型: cds 或 genomic")
    parser.add_argument("-o", "--output", required=True, help="输出目录")
    parser.add_argument("--primer3", default="primer3_core", help="Primer3 路径")

    # 引物参数
    parser.add_argument("--min-size", type=int, default=18, help="最小引物长度 (default: 18)")
    parser.add_argument("--opt-size", type=int, default=20, help="最优引物长度 (default: 20)")
    parser.add_argument("--max-size", type=int, default=25, help="最大引物长度 (default: 25)")
    parser.add_argument("--min-tm", type=float, default=55.0, help="最小 Tm (default: 55.0)")
    parser.add_argument("--opt-tm", type=float, default=60.0, help="最优 Tm (default: 60.0)")
    parser.add_argument("--max-tm", type=float, default=65.0, help="最大 Tm (default: 65.0)")
    parser.add_argument("--min-gc", type=float, default=40.0, help="最小 GC%% (default: 40.0)")
    parser.add_argument("--max-gc", type=float, default=60.0, help="最大 GC%% (default: 60.0)")
    parser.add_argument("--product-size", default="70-250", help="产物大小范围 (default: 70-250)")
    parser.add_argument("--target", default="100-500", help="扩增目标区域 (default: 100-500)")

    args = parser.parse_args()

    input_file = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("PGCP 引物设计")
    print("=" * 60)
    print(f"输入文件: {input_file}")
    print(f"序列类型: {args.type}")
    print(f"输出目录: {output_dir}")
    print("=" * 60)

    # 读取序列
    print("\n[1/3] 读取 FASTA 文件...")
    runner = Primer3Runner(primer3_path=args.primer3)
    sequences = runner.read_fasta(input_file)
    print(f"  读取到 {len(sequences)} 条序列")

    # 设计引物
    print("\n[2/3] 设计引物...")
    params = runner.default_params.copy()
    params["PRIMER_MIN_SIZE"] = args.min_size
    params["PRIMER_OPT_SIZE"] = args.opt_size
    params["PRIMER_MAX_SIZE"] = args.max_size
    params["PRIMER_MIN_TM"] = args.min_tm
    params["PRIMER_OPT_TM"] = args.opt_tm
    params["PRIMER_MAX_TM"] = args.max_tm
    params["PRIMER_MIN_GC"] = args.min_gc
    params["PRIMER_MAX_GC"] = args.max_gc
    params["PRIMER_PRODUCT_SIZE_RANGE"] = args.product_size
    params["SEQUENCE_TARGET"] = args.target

    # 验证参数（转换格式使其符合 primer3 要求）
    params = runner._validate_params(params)

    output_file = output_dir / f"{input_file.stem.replace('.fa', '').replace('.gz', '')}.primers.txt"
    results = runner.design_primers_for_sequences(sequences, output_file, params)

    # 统计
    print("\n[3/3] 完成!")
    success = sum(1 for r in results if r['status'] == 'success')
    total_pairs = sum(r.get('pair_count', 0) for r in results if r['status'] == 'success')

    print(f"\n结果统计:")
    print(f"  成功: {success}/{len(results)} 条序列")
    print(f"  引物对总数: {total_pairs}")
    print(f"  结果文件: {output_file}")
    print(f"  TSV文件: {output_file.with_suffix('.tsv')}")

    # 显示前3个结果
    print(f"\n前3个结果预览:")
    for r in results[:3]:
        print(f"  {r['seq_id']}: {r['status']}", end="")
        if r['status'] == 'success':
            print(f" ({r.get('pair_count', 0)} pairs)")
        else:
            print()


if __name__ == "__main__":
    main()