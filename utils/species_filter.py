#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
物种信息筛选与统计脚本
支持按目、科、属级别筛选，统计物种数量，导出多种格式
"""

import argparse
import sys
import pandas as pd
from pathlib import Path


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='物种信息筛选与统计工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 按目筛选
  python species_filter.py -l order -n Fabales
  
  # 按科筛选
  python species_filter.py -l family -n Fabaceae
  
  # 按属筛选
  python species_filter.py -l genus -n Acer
  
  # 统计各目物种数量
  python species_filter.py -l order --count
  
  # 筛选物种数量等于精确值的类别
  python species_filter.py -l family --count --exact 10
  
  # 筛选物种数量在区间 [min, max] 的类别
  python species_filter.py -l order --count --range 5 20
  
  # 导出为csv格式
  python species_filter.py -l family --count -f csv -o output.csv
        """
    )
    
    parser.add_argument('-i', '--input', 
                        default='/home/nizhu/wangwenhui/species_list_with_taxid.txt',
                        help='输入文件路径 (默认: /home/nizhu/wangwenhui/species_list_with_taxid.txt)')
    
    parser.add_argument('-l', '--level', 
                        choices=['order', 'family', 'genus', '目', '科', '属'],
                        required=True,
                        help='筛选级别: order/目, family/科, genus/属')
    
    parser.add_argument('-n', '--name',
                        help='筛选类别具体名称，例如: Fabales, Fabaceae, Acer')
    
    parser.add_argument('--count', 
                        action='store_true',
                        help='按分类级别统计物种数量')
    
    parser.add_argument('--exact',
                        type=int,
                        help='筛选物种数量等于精确值的类别')
    
    parser.add_argument('--range',
                        nargs=2,
                        type=int,
                        metavar=('MIN', 'MAX'),
                        help='筛选物种数量在区间 [min, max] 的类别')
    
    parser.add_argument('-f', '--format',
                        choices=['txt', 'csv', 'tsv', 'xlsx'],
                        default='xlsx',
                        help='输出格式 (默认: xlsx)')
    
    parser.add_argument('-o', '--output',
                        help='输出文件路径 (默认: 自动生成)')
    
    return parser.parse_args()


def load_data(input_file):
    """加载物种数据"""
    if not Path(input_file).exists():
        print(f"错误: 文件不存在 {input_file}")
        sys.exit(1)
    
    try:
        # 读取制表符分隔的文件
        df = pd.read_csv(input_file, sep='\t')
        return df
    except Exception as e:
        print(f"错误: 无法读取文件 - {e}")
        sys.exit(1)


def get_level_column(level):
    """将级别参数转换为列名"""
    level_map = {
        'order': 'Order',
        '目': 'Order',
        'family': 'Family',
        '科': 'Family',
        'genus': 'Clade',
        '属': 'Clade'
    }
    return level_map.get(level)


def filter_by_name(df, level_col, name):
    """按名称筛选"""
    filtered = df[df[level_col] == name].copy()
    return filtered


def count_species(df, level_col):
    """按分类级别统计物种数量"""
    # 统计每个类别的物种数量（去重）
    # 使用 Species 列统计物种数量
    counts = df.groupby(level_col)['Species'].nunique().reset_index()
    counts.columns = [level_col, 'Species_Count']
    counts = counts.sort_values('Species_Count', ascending=False)
    return counts


def filter_by_exact(counts, exact_val):
    """筛选物种数量等于精确值的类别"""
    return counts[counts['Species_Count'] == exact_val].copy()


def filter_by_range(counts, min_val, max_val):
    """筛选物种数量在区间的类别"""
    return counts[(counts['Species_Count'] >= min_val) & 
                  (counts['Species_Count'] <= max_val)].copy()


def generate_output_filename(level, name, format_type, count_mode):
    """生成输出文件名"""
    parts = [level]
    if name:
        parts.append(name)
    if count_mode:
        parts.append('count')
    
    filename = '_'.join(parts)
    
    ext_map = {
        'txt': '.txt',
        'csv': '.csv',
        'tsv': '.tsv',
        'xlsx': '.xlsx'
    }
    
    return filename + ext_map.get(format_type, '.xlsx')


def export_data(df, output_file, format_type):
    """导出数据到指定格式"""
    try:
        if format_type == 'txt':
            df.to_csv(output_file, sep='\t', index=False)
        elif format_type == 'csv':
            df.to_csv(output_file, index=False)
        elif format_type == 'tsv':
            df.to_csv(output_file, sep='\t', index=False)
        elif format_type == 'xlsx':
            df.to_excel(output_file, index=False)
        
        print(f"结果已导出到: {output_file}")
    except Exception as e:
        print(f"错误: 导出失败 - {e}")
        sys.exit(1)


def main():
    args = parse_args()
    
    # 加载数据
    print(f"正在加载数据: {args.input}")
    df = load_data(args.input)
    print(f"共加载 {len(df)} 条记录")
    
    # 获取级别列名
    level_col = get_level_column(args.level)
    print(f"筛选级别: {args.level} ({level_col})")
    
    result_df = None
    
    # 按名称筛选
    if args.name:
        print(f"筛选名称: {args.name}")
        result_df = filter_by_name(df, level_col, args.name)
        print(f"筛选结果: {len(result_df)} 条记录")
        
        if len(result_df) == 0:
            print("警告: 未找到匹配的记录")
            return
    
    # 统计模式
    if args.count:
        if result_df is not None:
            # 在筛选结果上统计
            counts = count_species(result_df, level_col)
        else:
            # 在全表上统计
            counts = count_species(df, level_col)
        
        print(f"\n共找到 {len(counts)} 个{args.level}类别")
        
        # 应用精确值筛选
        if args.exact is not None:
            counts = filter_by_exact(counts, args.exact)
            print(f"物种数量等于 {args.exact} 的类别: {len(counts)} 个")
        
        # 应用区间筛选
        if args.range is not None:
            min_val, max_val = args.range
            counts = filter_by_range(counts, min_val, max_val)
            print(f"物种数量在 [{min_val}, {max_val}] 区间的类别: {len(counts)} 个")
        
        result_df = counts
        print("\n统计结果预览:")
        print(result_df.to_string())
    else:
        # 非统计模式，但可能有精确值或区间筛选（需要统计后再筛选）
        if args.exact is not None or args.range is not None:
            print("警告: --exact 和 --range 参数需要配合 --count 使用")
    
    # 确定输出文件
    if args.output:
        output_file = args.output
    else:
        output_file = generate_output_filename(
            args.level, 
            args.name, 
            args.format,
            args.count
        )
    
    # 导出结果
    if result_df is not None and len(result_df) > 0:
        export_data(result_df, output_file, args.format)
    else:
        print("没有可导出的结果")


if __name__ == '__main__':
    main()
