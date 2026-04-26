#!/usr/bin/env python3
"""
整合基因组功能注释各模块的结果

各模块输出标准化命名:
  {物种名}_geneid_protid_mapping.{fmt}  - 基因ID与蛋白ID映射
  {物种名}_coordinates.tsv               - 坐标信息
  {物种名}_cds_pep.{fmt}                 - CDS和蛋白序列
  {物种名}_protein_properties.{fmt}      - 蛋白理化性质
  {物种名}_eggnog_annotation.tsv         - eggnog-mapper功能注释

用法:
  python integrate_outputs.py -i <结果目录> -o <输出目录>
  python integrate_outputs.py -i result/annotation -o result/integrated

输出:
  {物种名}_integrated.xlsx  - 整合后的完整注释表
  integration_report.txt   - 整合报告
"""

import os
import argparse
import pandas as pd
from pathlib import Path

# 各模块文件后缀
MODULE_FILES = {
    'mapping': '{species}_geneid_protid_mapping.xlsx',
    'coordinates': '{species}_coordinates.tsv',
    'cds_pep': '{species}_cds_pep.xlsx',
    'protein_properties': '{species}_protein_properties.xlsx',
    'eggnog': '{species}_eggnog_annotation.tsv',
}

def find_species_dirs(root_dir):
    """查找所有物种目录"""
    root = Path(root_dir)
    if not root.exists():
        return []
    return [d for d in root.iterdir() if d.is_dir() and not d.name.startswith('.')]

def check_module_outputs(species_dir):
    """检查某物种各模块输出情况"""
    results = {}
    for module, pattern in MODULE_FILES.items():
        pattern_local = pattern.format(species=species_dir.name)
        # 同目录下查找
        file_path = species_dir / pattern_local
        if file_path.exists():
            results[module] = file_path
        else:
            results[module] = None
    return results

def load_table(file_path):
    """加载表格文件，支持 xlsx/tsv/csv 格式"""
    try:
        if file_path.suffix == '.xlsx':
            return pd.read_excel(file_path)
        elif file_path.suffix == '.tsv':
            return pd.read_csv(file_path, sep='\t')
        else:
            return pd.read_csv(file_path)
    except Exception as e:
        print(f"    加载失败: {e}")
        return None

def integrate_species(species_dir, module_paths):
    """整合单个物种的各模块结果"""
    species_name = species_dir.name
    integrated_data = {}

    # 加载各模块数据
    for module, file_path in module_paths.items():
        if file_path and file_path.exists():
            try:
                df = load_table(file_path)
                if df is None:
                    continue
                if module == 'cds_pep':
                    for col in df.columns:
                        if col not in ['protein_id', 'species']:
                            df.rename(columns={col: f'cds_pep_{col}'}, inplace=True)
                    for _, row in df.iterrows():
                        pid = row['protein_id']
                        if pid not in integrated_data:
                            integrated_data[pid] = {'protein_id': pid}
                        integrated_data[pid].update(row.to_dict())
                elif module == 'protein_properties':
                    for _, row in df.iterrows():
                        pid = row.get('protein_id')
                        if pid and pid in integrated_data:
                            integrated_data[pid].update(row.to_dict())
                else:
                    for _, row in df.iterrows():
                        pid = row.get('protein_id') or row.get('gene_id')
                        if pid and pid not in integrated_data:
                            integrated_data[pid] = {'protein_id': pid}
                        if pid in integrated_data:
                            integrated_data[pid].update(row.to_dict())
            except Exception as e:
                print(f"    [{module}] 加载失败: {e}")

    return integrated_data

def main():
    parser = argparse.ArgumentParser(
        description='整合基因组功能注释各模块结果',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
示例:
  python integrate_annotation.py -i result/annotation -o result/integrated
  python integrate_annotation.py -i result/annotation -o result/integrated -f csv

输出文件:
  {物种名}_integrated.tsv  - 整合后的完整注释表
  integration_report.txt   - 整合报告，包含各模块覆盖情况
        """,
    )
    parser.add_argument('-i', '--input', required=True,
                        help='输入目录，包含各物种的注释结果')
    parser.add_argument('-o', '--output', required=True,
                        help='输出目录，存放整合结果')
    parser.add_argument('-f', '--format', default='xlsx',
                        choices=['tsv', 'csv', 'xlsx'],
                        help='输出格式 (默认: xlsx)')

    args = parser.parse_args()

    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)

    # 查找物种目录
    species_dirs = find_species_dirs(args.input)
    if not species_dirs:
        print(f"错误: 未找到物种目录 {args.input}")
        return

    print(f"发现 {len(species_dirs)} 个物种目录")

    # 汇总报告
    report_lines = []
    report_lines.append("=" * 60)
    report_lines.append("基因组功能注释整合报告")
    report_lines.append("=" * 60)
    report_lines.append(f"输入目录: {args.input}")
    report_lines.append(f"输出目录: {args.output}")
    report_lines.append(f"处理时间: {pd.Timestamp.now()}")
    report_lines.append("")

    success_count = 0
    fail_count = 0

    for species_dir in sorted(species_dirs):
        print(f"\n处理物种: {species_dir.name}")

        # 检查各模块输出
        module_paths = check_module_outputs(species_dir)

        # 报告模块覆盖情况
        covered = [m for m, p in module_paths.items() if p]
        missing = [m for m, p in module_paths.items() if not p]
        print(f"  已完成: {', '.join(covered) if covered else '无'}")
        if missing:
            print(f"  缺失: {', '.join(missing)}")

        report_lines.append(f"\n{species_dir.name}:")
        report_lines.append(f"  已完成: {', '.join(covered) if covered else '无'}")
        report_lines.append(f"  缺失: {', '.join(missing) if missing else '无'}")

        if not covered:
            report_lines.append("  跳过 (无任何输出)")
            fail_count += 1
            continue

        # 整合数据
        integrated_data = integrate_species(species_dir, module_paths)

        if integrated_data:
            # 输出整合结果
            df = pd.DataFrame(list(integrated_data.values()))

            # 按格式输出
            out_file = os.path.join(args.output, f"{species_dir.name}_integrated.{args.format}")
            if args.format == 'csv':
                df.to_csv(out_file, index=False, encoding='utf-8-sig')
            elif args.format == 'xlsx':
                df.to_excel(out_file, index=False)
            else:
                df.to_csv(out_file, index=False, sep='\t')

            print(f"  整合完成: {len(df)} 条记录 -> {out_file}")
            report_lines.append(f"  整合记录: {len(df)} 条")
            success_count += 1
        else:
            print(f"  整合失败: 无有效数据")
            report_lines.append("  整合失败: 无有效数据")
            fail_count += 1

    # 保存报告
    report_file = os.path.join(args.output, 'integration_report.txt')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

    print(f"\n{'=' * 60}")
    print("整合完成!")
    print(f"成功: {success_count} 个物种")
    print(f"失败: {fail_count} 个物种")
    print(f"报告: {report_file}")

if __name__ == '__main__':
    main()