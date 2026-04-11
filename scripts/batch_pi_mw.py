#!/usr/bin/env python3
import os
import pandas as pd
from Bio import SeqIO
from Bio.SeqUtils.ProtParam import ProteinAnalysis

def main():
    root_dir = "."
    print(f"搜索目录: {root_dir}")
    found = 0
    for dirpath, _, filenames in os.walk(root_dir):
        # 跳过 ncbi_dataset 目录及其子目录
        if 'ncbi_dataset' in dirpath.split(os.sep):
            continue
        for f in filenames:
            if f.endswith('_protein.fa') or f == 'protein.fa':
                found += 1
                fasta_path = os.path.join(dirpath, f)
                print(f"\n找到文件: {fasta_path}")
                results = []
                for record in SeqIO.parse(fasta_path, "fasta"):
                    try:
                        pa = ProteinAnalysis(str(record.seq))
                        results.append({
                            'gene_id': record.id,
                            'protein_length': len(record.seq),
                            'molecular_weight': round(pa.molecular_weight(), 2),
                            'isoelectric_point': round(pa.isoelectric_point(), 2)
                        })
                    except Exception as e:
                        print(f"  跳过 {record.id}: {e}")
                if results:
                    out_file = fasta_path.replace('.fa', '_physicochemical.xlsx')
                    pd.DataFrame(results).to_excel(out_file, index=False)
                    print(f"  已保存: {out_file} ({len(results)} 条)")
                else:
                    print("  警告: 没有成功计算任何序列")
    if found == 0:
        print("未找到任何 *_protein.fa 或 protein.fa 文件")

if __name__ == "__main__":
    main()