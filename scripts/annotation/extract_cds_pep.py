#!/usr/bin/env python3
"""
从 protein.faa 和 cds.fna 中提取序列，根据 protein_id 匹配

输出格式: protein_id, species, cds, pep

输出命名: {物种名}_cds_pep.{format}

支持两种模式:
1. 单物种模式: 处理指定目录下的 protein.faa 和 cds.fna
2. 批量模式: 自动遍历父目录下的所有物种子目录，批量处理

输出结构:
    输出目录/
    ├── Species_A/
    │   └── Species_A_cds_pep.xlsx
    ├── Species_B/
    │   └── Species_B_cds_pep.xlsx
    └── Species_C/
        (空目录，缺少必要文件)

用法:
    python extract_cds_pep.py                          # 批量处理genomes目录 (默认xlsx格式)
    python extract_cds_pep.py -b /path/to/parent       # 批量模式指定源目录
    python extract_cds_pep.py -d /custom/output       # 指定输出目录
    python extract_cds_pep.py -f csv                   # 输出CSV格式
    python extract_cds_pep.py -i /path/to/species     # 单物种模式
"""

import re
import csv
import argparse
import os
import glob

try:
    from Bio.Seq import Seq
    HAS_BIOPYTHON = True
except ImportError:
    HAS_BIOPYTHON = False

def self_check(pep_data, cds_data, common_ids):
    """自检：检查蛋白ID、CDS和PEP的对应关系"""
    print("\n===== 自检开始 =====")
    errors = []
    warnings = []
    
    # 1. 检查ID对应关系
    print("\n[1] 检查蛋白ID对应关系...")
    pep_only_ids = set(pep_data.keys()) - set(cds_data.keys())
    cds_only_ids = set(cds_data.keys()) - set(pep_data.keys())
    
    if pep_only_ids:
        warnings.append(f"  ⚠ 有 {len(pep_only_ids)} 个蛋白ID仅在protein.faa中存在")
        print(f"  ⚠ 有 {len(pep_only_ids)} 个蛋白ID仅在protein.faa中存在")
        print(f"    示例: {', '.join(sorted(pep_only_ids)[:5])}")
    if cds_only_ids:
        warnings.append(f"  ⚠ 有 {len(cds_only_ids)} 个蛋白ID仅在cds中存在")
        print(f"  ⚠ 有 {len(cds_only_ids)} 个蛋白ID仅在cds中存在")
        print(f"    示例: {', '.join(sorted(cds_only_ids)[:5])}")
    if not pep_only_ids and not cds_only_ids:
        print("  ✓ 所有蛋白ID在protein和cds中均存在")
    
    # 2. 检查序列非空
    print("\n[2] 检查序列是否为空...")
    empty_pep = [pid for pid in common_ids if not pep_data[pid][1]]
    empty_cds = [pid for pid in common_ids if not cds_data[pid]]
    if empty_pep:
        errors.append(f"  ✗ 有 {len(empty_pep)} 个蛋白的PEP序列为空")
        print(f"  ✗ 有 {len(empty_pep)} 个蛋白的PEP序列为空")
    if empty_cds:
        errors.append(f"  ✗ 有 {len(empty_cds)} 个蛋白的CDS序列为空")
        print(f"  ✗ 有 {len(empty_cds)} 个蛋白的CDS序列为空")
    if not empty_pep and not empty_cds:
        print("  ✓ 所有序列均非空")
    
    # 3. 验证CDS翻译是否与PEP匹配
    print("\n[3] 验证CDS能否正确翻译为PEP...")
    if HAS_BIOPYTHON:
        mismatch_count = 0
        mismatch_examples = []
        stop_codon_count = 0
        for pid in common_ids:
            cds = cds_data[pid]
            _, pep = pep_data[pid]
            if not cds or not pep:
                continue
            translated = str(Seq(cds).translate())
            # 比较时需要去除终止密码子
            if translated.rstrip('*') == pep.rstrip('*'):
                continue
            else:
                mismatch_count += 1
                if len(mismatch_examples) < 5:
                    mismatch_examples.append(pid)
                # 检查是否是终止密码子导致的不匹配
                if translated.rstrip('*').endswith(pep.rstrip('*')) or \
                   pep.rstrip('*').endswith(translated.rstrip('*')):
                    stop_codon_count += 1
        
        if mismatch_count == 0:
            print(f"  ✓ 所有 {len(common_ids)} 个CDS均可正确翻译为PEP")
        else:
            errors.append(f"  ✗ 有 {mismatch_count} 个CDS翻译后与PEP不匹配")
            print(f"  ✗ 有 {mismatch_count} 个CDS翻译后与PEP不匹配")
            print(f"    不匹配示例: {', '.join(mismatch_examples)}")
            if stop_codon_count > 0:
                warnings.append(f"  ⚠ 其中 {stop_codon_count} 个可能是终止密码子差异")
                print(f"  ⚠ 其中 {stop_codon_count} 个可能是终止密码子差异")
    else:
        warnings.append("  ⚠ 未安装Biopython，跳过翻译验证")
        print("  ⚠ 未安装Biopython，跳过翻译验证")
        print("    安装命令: pip install biopython")
    
    # 4. 检查序列长度合理性
    print("\n[4] 检查序列长度合理性...")
    length_issues = []
    for pid in common_ids:
        cds = cds_data[pid]
        _, pep = pep_data[pid]
        if cds and pep:
            # CDS长度应该是PEP长度的3倍左右（允许一些差异）
            expected_cds_len = len(pep) * 3
            if len(cds) < expected_cds_len * 0.5 or len(cds) > expected_cds_len * 2:
                length_issues.append(pid)
    if length_issues:
        warnings.append(f"  ⚠ 有 {len(length_issues)} 个序列长度比例异常")
        print(f"  ⚠ 有 {len(length_issues)} 个序列长度比例异常")
        print(f"    示例: {', '.join(length_issues[:5])}")
    else:
        print("  ✓ 所有CDS/PEP长度比例正常")
    
    # 汇总
    print("\n===== 自检结果汇总 =====")
    if errors:
        print(f"错误: {len(errors)} 项")
        for e in errors:
            print(e)
    if warnings:
        print(f"警告: {len(warnings)} 项")
        for w in warnings:
            print(w)
    if not errors and not warnings:
        print("✓ 自检通过，未发现问题")
    
    return len(errors) == 0

def verify_with_result_file(pep_data, cds_data, result_file):
    """与已有结果文件比对，验证CDS和PEP是否一致"""
    print(f"\n===== 与结果文件比对 =====")
    print(f"比对文件: {result_file}")
    
    result_data = {}
    with open(result_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row['protein_id']
            result_data[pid] = {'cds': row['cds'], 'pep': row['pep']}
    
    print(f"  结果文件共有 {len(result_data)} 条记录")
    
    common_ids = set(pep_data.keys()) & set(cds_data.keys()) & set(result_data.keys())
    print(f"  共有 {len(common_ids)} 个蛋白ID可比对")
    
    # 比对CDS
    cds_match = 0
    cds_mismatch = 0
    cds_mismatch_examples = []
    
    # 比对PEP
    pep_match = 0
    pep_mismatch = 0
    pep_mismatch_examples = []
    
    for pid in common_ids:
        # 比对CDS
        if cds_data[pid] == result_data[pid]['cds']:
            cds_match += 1
        else:
            cds_mismatch += 1
            if len(cds_mismatch_examples) < 3:
                cds_mismatch_examples.append(pid)
        
        # 比对PEP
        _, pep = pep_data[pid]
        if pep == result_data[pid]['pep']:
            pep_match += 1
        else:
            pep_mismatch += 1
            if len(pep_mismatch_examples) < 3:
                pep_mismatch_examples.append(pid)
    
    print(f"\n[1] CDS比对结果:")
    print(f"  ✓ 一致: {cds_match}")
    print(f"  ✗ 不一致: {cds_mismatch}")
    if cds_mismatch_examples:
        print(f"    不一致示例: {', '.join(cds_mismatch_examples)}")
    
    print(f"\n[2] PEP比对结果:")
    print(f"  ✓ 一致: {pep_match}")
    print(f"  ✗ 不一致: {pep_mismatch}")
    if pep_mismatch_examples:
        print(f"    不一致示例: {', '.join(pep_mismatch_examples)}")
    
    print("\n===== 比对结果汇总 =====")
    if cds_mismatch == 0 and pep_mismatch == 0:
        print("✓ 所有CDS和PEP序列均与结果文件一致")
        return True
    else:
        print(f"✗ 发现不一致: CDS {cds_mismatch}个, PEP {pep_mismatch}个")
        return False

SUPPORTED_FORMATS = ['csv', 'xlsx', 'tsv', 'txt']
DEFAULT_FORMAT = 'xlsx'
DEFAULT_GENOMES_DIR = '/DATA/data2/downloads/genomes'
DEFAULT_OUTPUT_DIR = '/home/nizhu/hechenxi/result'

def parse_faa(filepath):
    """解析 protein.faa，返回 {protein_id: (species, pep_seq)}"""
    data = {}
    current_pid, current_species, current_seq = None, None, []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('>'):
                if current_pid:
                    data[current_pid] = (current_species, ''.join(current_seq))
                match = re.match(r'^>(\S+)\s+.*\[([^\]]+)\]', line)
                if match:
                    current_pid, current_species = match.group(1), match.group(2)
                    current_seq = []
                else:
                    current_pid = None
            elif line and current_pid:
                current_seq.append(line)
        if current_pid:
            data[current_pid] = (current_species, ''.join(current_seq))
    return data

def parse_cds(filepath):
    """解析 cds.fna，返回 {protein_id: cds_seq}"""
    data = {}
    current_pid, current_seq = None, []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('>'):
                if current_pid:
                    data[current_pid] = ''.join(current_seq)
                # 匹配 [protein_id=xxx] 格式
                match = re.search(r'\[protein_id=(\S+)\]', line)
                if match:
                    current_pid = match.group(1)
                    current_seq = []
                else:
                    current_pid = None
            elif line and current_pid:
                current_seq.append(line)
        if current_pid:
            data[current_pid] = ''.join(current_seq)
    return data

def find_input_files(species_dir):
    """在物种目录下查找 protein.faa 和 cds.fna 文件"""
    faa_files = glob.glob(os.path.join(species_dir, '*_protein.faa'))
    cds_files = glob.glob(os.path.join(species_dir, '*_cds.fna'))
    
    faa_file = faa_files[0] if faa_files else None
    cds_file = cds_files[0] if cds_files else None
    
    return faa_file, cds_file

def find_species_dirs(parent_dir):
    """在父目录下查找所有物种子目录"""
    species_dirs = []
    for item in os.listdir(parent_dir):
        item_path = os.path.join(parent_dir, item)
        if os.path.isdir(item_path):
            species_dirs.append((item, item_path))  # 返回 (物种名, 路径)
    return species_dirs

def process_single_species(source_species_dir, output_species_dir, output_format, verify=True, verbose=True):
    """处理单个物种的数据"""
    species_name = os.path.basename(source_species_dir)
    faa_file, cds_file = find_input_files(source_species_dir)
    
    if not faa_file or not cds_file:
        if verbose:
            print(f"  跳过 {species_name}: 缺少必要文件")
        return False, 0
    
    if verbose:
        print(f"\n处理物种: {species_name}")
        print(f"  protein.faa: {faa_file}")
        print(f"  cds.fna: {cds_file}")
    
    # 解析文件
    if verbose:
        print("  解析 protein.faa...")
    pep_data = parse_faa(faa_file)
    if verbose:
        print(f"    解析到 {len(pep_data)} 个蛋白")
    
    if verbose:
        print("  解析 cds.fna...")
    cds_data = parse_cds(cds_file)
    if verbose:
        print(f"    解析到 {len(cds_data)} 个 CDS")
    
    common_ids = set(pep_data.keys()) & set(cds_data.keys())
    if verbose:
        print(f"  匹配到 {len(common_ids)} 个共同蛋白ID")
    
    if len(common_ids) == 0:
        if verbose:
            print(f"  ✗ {species_name}: 没有匹配的蛋白ID")
        return False, 0
    
    # 自检
    if verify and HAS_BIOPYTHON:
        self_check(pep_data, cds_data, common_ids)
    
    # 准备数据
    headers = ['protein_id', 'species', 'cds', 'pep']
    rows = []
    for pid in sorted(common_ids):
        species, pep = pep_data[pid]
        cds = cds_data[pid]
        rows.append([pid, species, cds, pep])
    
    # 输出到物种目录下
    output_file = os.path.join(output_species_dir, f'{species_name}_cds_pep.{output_format}')
    if verbose:
        print(f"  写入结果到 {output_file} (格式: {output_format})...")
    
    if output_format == 'xlsx':
        try:
            import openpyxl
            from openpyxl import Workbook
        except ImportError:
            if verbose:
                print("  错误: 需要安装 openpyxl 库来处理 xlsx 格式")
            return False, 0
        
        wb = Workbook()
        ws = wb.active
        ws.title = 'sequences'
        ws.append(headers)
        for row in rows:
            ws.append(row)
        wb.save(output_file)
    else:
        delimiter = '\t' if output_format == 'tsv' else ','
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=delimiter)
            writer.writerow(headers)
            writer.writerows(rows)
    
    if verbose:
        print(f"  ✓ 完成! 共 {len(common_ids)} 条记录")
    
    return True, len(common_ids)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='从 protein.faa 和 cds.fna 中提取序列，批量处理物种数据',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
支持的输出格式: csv, xlsx, tsv, txt

示例:
    python extract_cds_pep.py                           # 批量模式: 处理genomes目录 (默认xlsx格式)
    python extract_cds_pep.py -b /path/to/parent       # 批量模式指定父目录
    python extract_cds_pep.py -i /path/to/species      # 单物种模式
    python extract_cds_pep.py -f csv                    # 输出CSV格式
        '''
    )
    parser.add_argument('-i', '--input', 
                        help='单物种模式: 物种目录路径')
    parser.add_argument('-b', '--batch', 
                        help='批量模式: 源父目录路径')
    parser.add_argument('-o', '--output', default='result',
                        help='输出文件名 (不含扩展名, 默认: result)')
    parser.add_argument('-d', '--dir', default=DEFAULT_OUTPUT_DIR,
                        help=f'输出目录路径 (默认: {DEFAULT_OUTPUT_DIR})')
    parser.add_argument('-f', '--format', choices=SUPPORTED_FORMATS, default=DEFAULT_FORMAT,
                        help=f'输出文件格式 (默认: xlsx)')
    parser.add_argument('--no-verify', action='store_true',
                        help='跳过自检步骤')
    parser.add_argument('-v', '--verify-result',
                        help='与已有的结果文件比对，验证CDS和PEP是否一致')
    return parser.parse_args()

def main():
    args = parse_args()
    
    verify = not args.no_verify
    if verify and not HAS_BIOPYTHON:
        print("警告: 未安装 Biopython，跳过自检功能")
        print("请运行: pip install biopython")
        verify = False
    
    # 确定输出格式
    output_format = args.format
    
    # 创建输出目录
    output_base_dir = args.dir
    os.makedirs(output_base_dir, exist_ok=True)
    
    if args.input:
        # 单物种模式
        source_species_dir = args.input
        species_name = os.path.basename(source_species_dir)
        # output_base_dir 直接作为物种目录，不需要再拼接species_name
        output_species_dir = output_base_dir
        os.makedirs(output_species_dir, exist_ok=True)
        output_file = os.path.join(output_species_dir, f'{species_name}_cds_pep.{output_format}')
        success, count = process_single_species(source_species_dir, output_species_dir, output_format, verify)
        if success:
            print(f"\n✓ 处理完成! 结果保存在: {output_file}")
        else:
            print(f"\n⚠ 物种 {species_name} 缺少必要文件，已创建空目录: {output_species_dir}")
    else:
        # 批量模式
        if args.batch:
            source_parent_dir = args.batch
        else:
            source_parent_dir = DEFAULT_GENOMES_DIR
        
        print(f"===== 批量处理模式 =====")
        print(f"源目录: {source_parent_dir}")
        print(f"输出目录: {output_base_dir}")
        
        if not os.path.exists(source_parent_dir):
            print(f"错误: 目录不存在: {source_parent_dir}")
            return
        
        # 获取所有物种目录
        all_species = find_species_dirs(source_parent_dir)
        print(f"共 {len(all_species)} 个物种目录")
        
        if not all_species:
            print("错误: 没有找到有效的物种目录")
            return
        
        # 统计
        total_success = 0
        total_skipped = 0
        total_records = 0
        
        for species_name, source_species_dir in all_species:
            # 创建输出物种目录
            output_species_dir = os.path.join(output_base_dir, species_name)
            os.makedirs(output_species_dir, exist_ok=True)
            
            # 尝试处理
            output_file = os.path.join(output_species_dir, f'{species_name}_cds_pep.{output_format}')
            success, count = process_single_species(source_species_dir, output_species_dir, output_format, verify, verbose=True)
            
            if success:
                total_success += 1
                total_records += count
            else:
                total_skipped += 1
        
        # 汇总
        print("\n" + "=" * 50)
        print("===== 批量处理汇总 =====")
        print(f"  成功处理: {total_success} 个物种")
        print(f"  跳过(缺文件): {total_skipped} 个物种")
        print(f"  总记录: {total_records} 条")
        print(f"\n输出目录: {output_base_dir}")
        print(f"每个物种对应一个子目录，表格文件名为: {args.output}.{output_format}")

if __name__ == '__main__':
    main()
