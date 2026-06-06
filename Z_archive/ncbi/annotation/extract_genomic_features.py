#!/usr/bin/env python3
"""
extract_genomic_features.py - 批量提取基因组结构信息

处理流程:
  1. GFF/GBFF -> BED   (注释文件转BED格式)
  2. FNA -> FASTA      (按BED坐标从基因组提取基因序列)
  3. BED + FASTA -> 表格 (合并为结构化数据文件)

输出列: gene_id | chromosome | start_position | end_position | strand | species | sequence

用法:
  批量:   python extract_genomic_features.py [-i <根目录>] [-o <输出根目录>] [-f xlsx]
  单物种: python extract_genomic_features.py -i <注释文件> <基因组文件> -o <输出路径> -s <物种名> [-f csv]
  帮助:   python extract_genomic_features.py -h

输出格式:
  支持 xlsx (默认), tsv, csv
"""

import sys
import os
import re
import argparse
from Bio import SeqIO
import pandas as pd

_RC = str.maketrans('ATCGatcg', 'TAGCtagc')
DEFAULT_INPUT_DIR = '/home/nizhu/zhangyan/downloads/genomes'
DEFAULT_OUTPUT_FORMAT = 'xlsx'

# 注释/基因组文件搜索优先级
ANN_EXTS = ['.bed', '.gff', '.gff3', '.gbff']
GENOME_EXTS = ['.fna', '.fa', '.fasta', '.faa']


def reverse_complement(seq):
    """DNA反向互补"""
    return seq.translate(_RC)[::-1]


def stale(target, source, force=False):
    """目标需要重新生成: force / 不存在 / 源更新"""
    return force or not os.path.exists(target) or os.path.getmtime(target) < os.path.getmtime(source)


def find_file(directory, name, exts):
    """按扩展名优先级查找文件，返回首个匹配或None"""
    for ext in exts:
        path = os.path.join(directory, name + ext)
        if os.path.exists(path):
            return path
    return None


# ========== Step 1: 注释文件 -> BED ==========

def parse_bed(bed_file):
    """解析BED -> [(gene_id, chrom, start, end, strand)]，重复ID只保留首条"""
    genes, seen = [], set()
    with open(bed_file) as f:
        for line in f:
            parts = line.split('\t')
            if len(parts) < 6 or parts[3].startswith('#'):
                continue
            gid = parts[3]
            if gid not in seen:
                seen.add(gid)
                genes.append((gid, parts[0], int(parts[1]), int(parts[2]), parts[5]))
    return genes


def _write_bed_line(fout, chrom, start, end, gid, strand):
    fout.write(f"{chrom}\t{start - 1}\t{end}\t{gid}\t.\t{strand}\n")


def convert_gff_to_bed(gff_file, bed_file):
    """GFF/GFF3 -> BED (1-based -> 0-based)，提取gene行"""
    count = 0
    with open(gff_file) as fin, open(bed_file, 'w') as fout:
        for line in fin:
            parts = line.split('\t')
            if len(parts) < 9 or parts[2] != 'gene':
                continue
            attrs = parts[8]
            gid = None
            if 'ID=' in attrs:
                gid = attrs.split('ID=', 1)[1].split(';', 1)[0].split(':', 1)[0]
            elif 'Name=' in attrs:
                gid = attrs.split('Name=', 1)[1].split(';', 1)[0]
            if gid:
                _write_bed_line(fout, parts[0], int(parts[3]), int(parts[4]), gid, parts[6])
                count += 1
    print(f"    GFF->BED: {count} genes")


def convert_gbff_to_bed(gbff_file, bed_file):
    """GBFF -> BED，从GenBank flat file提取gene位置"""
    count = 0
    chrom = gid = None
    start = end = 0
    strand = '+'
    with open(gbff_file) as fin, open(bed_file, 'w') as fout:
        for line in fin:
            if line.startswith('LOCUS'):
                chrom = line.split()[1]
                gid = None
            elif line.startswith('     gene ') and chrom:
                gene_info = line.strip().split()[1]
                gid = None  # 重置，等待匹配locus_tag
                m = re.match(r'complement\((\d+)\.\.(\d+)\)', gene_info)
                if m:
                    strand, start, end = '-', int(m.group(1)), int(m.group(2))
                else:
                    m = re.match(r'(\d+)\.\.(\d+)', gene_info)
                    if m:
                        strand, start, end = '+', int(m.group(1)), int(m.group(2))
            elif 'locus_tag="' in line and gid is None and chrom:
                m = re.search(r'locus_tag="([^"]+)"', line)
                if m:
                    gid = m.group(1)
                    _write_bed_line(fout, chrom, start, end, gid, strand)
                    count += 1
    print(f"    GBFF->BED: {count} genes")


def prepare_bed(ann_file, force=False):
    """注释文件 -> 基因列表 [(gene_id, chrom, start, end, strand)]"""
    ext = os.path.splitext(ann_file)[1].lower()
    if ext == '.bed':
        return parse_bed(ann_file)
    if ext not in ('.gff', '.gff3', '.gbff'):
        print(f"    错误: 不支持的注释格式 {ext}")
        return None
    bed_file = os.path.splitext(ann_file)[0] + '.bed'
    if stale(bed_file, ann_file, force):
        (convert_gff_to_bed if ext in ('.gff', '.gff3') else convert_gbff_to_bed)(ann_file, bed_file)
    return parse_bed(bed_file)


# ========== Step 2: FNA -> FASTA ==========

def extract_genes_from_fna(genes, fna_file, output_fasta):
    """按BED坐标从FNA提取基因序列，负链反向互补"""
    genome = {r.id: str(r.seq) for r in SeqIO.parse(fna_file, "fasta")}
    extracted, missing = 0, set()
    with open(output_fasta, 'w') as out:
        for gid, chrom, start, end, strand in genes:
            if chrom not in genome:
                missing.add(chrom)
                continue
            seq = genome[chrom][start:end]
            if strand == '-':
                seq = reverse_complement(seq)
            out.write(f">{gid}::{chrom}:{start}-{end}\n{seq}\n")
            extracted += 1
    msg = f"    FNA->FASTA: {extracted} genes"
    if missing:
        msg += f", {len(missing)} chrom未匹配"
    print(msg)


def prepare_fasta(genes, genome_file, force=False):
    """基因组文件 -> FASTA路径"""
    ext = os.path.splitext(genome_file)[1].lower()
    if ext in ('.fasta', '.faa'):
        return genome_file
    if ext in ('.fna', '.fa'):
        fasta_file = os.path.splitext(genome_file)[0] + '_genes.fasta'
        if stale(fasta_file, genome_file, force):
            extract_genes_from_fna(genes, genome_file, fasta_file)
        return fasta_file
    print(f"    错误: 不支持的基因组格式 {ext}")
    return None


# ========== Step 3: BED + FASTA -> 表格 ==========

def merge_to_output(genes, fasta_file, output_file, species, output_fmt='xlsx'):
    """合并为表格文件

    输出列:
      gene_id | chromosome | start_position | end_position | strand | species | sequence

    输出命名: {物种名}_coordinates.{fmt}
    """
    gene_info = {g[0]: g[1:] for g in genes}
    matched = 0

    # 收集数据
    rows = []
    for rec in SeqIO.parse(fasta_file, "fasta"):
        gid = rec.id.split('::')[0]
        if gid in gene_info:
            chrom, start, end, strand = gene_info[gid]
            rows.append({
                'gene_id': gid,
                'chromosome': chrom,
                'start_position': start,
                'end_position': end,
                'strand': strand,
                'species': species,
                'sequence': str(rec.seq)
            })
            matched += 1

    if not rows:
        print(f"    警告: 无匹配数据")
        return False

    # 创建DataFrame
    df = pd.DataFrame(rows)

    # 确保列顺序
    columns = ['gene_id', 'chromosome', 'start_position', 'end_position', 'strand', 'species', 'sequence']

    # 输出文件
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)

    if output_fmt == 'xlsx':
        df.to_excel(output_file, index=False)
    elif output_fmt == 'tsv':
        df.to_csv(output_file, sep='\t', index=False)
    elif output_fmt == 'csv':
        df.to_csv(output_file, index=False)
    else:
        print(f"    错误: 不支持的格式 {output_fmt}")
        return False

    print(f"    合并完成: {matched} genes -> {output_file}")
    return True


# ========== 批量处理 ==========

def process_species(species_dir, name, output_dir=None, output_fmt='xlsx', force=False):
    """处理单个物种子目录"""
    print(f"\n[{name}]")
    ann = find_file(species_dir, f'{name}_annotation', ANN_EXTS)
    if not ann:
        print("  跳过: 无注释文件")
        return False
    genome = find_file(species_dir, f'{name}_genome', GENOME_EXTS)
    if not genome:
        print("  跳过: 无基因组文件")
        return False

    # Step 1: 注释 -> 基因列表
    print(f"  [1] 注释->BED: {os.path.basename(ann)}")
    genes = prepare_bed(ann, force)
    if not genes:
        return False

    # Step 2: 基因组 -> FASTA
    print(f"  [2] 基因组->FASTA: {os.path.basename(genome)}")
    fasta_file = prepare_fasta(genes, genome, force)
    if not fasta_file:
        return False

    # Step 3: 合并 -> 输出文件
    ext = output_fmt
    if output_dir:
        out_path = os.path.join(output_dir, name, f"{name}_coordinates.{ext}")
    else:
        out_path = os.path.join(species_dir, f"{name}_coordinates.{ext}")
    print(f"  [3] 合并->{output_fmt.upper()}")
    merge_to_output(genes, fasta_file, out_path, name, output_fmt)
    return True


def batch_process(root_dir, output_dir=None, output_fmt='xlsx', force=False):
    """遍历根目录下所有物种子目录"""
    root_dir = os.path.abspath(root_dir)
    if not os.path.isdir(root_dir):
        sys.exit(f"错误: 目录不存在: {root_dir}")
    dirs = sorted(d for d in os.listdir(root_dir)
                  if os.path.isdir(os.path.join(root_dir, d)) and not d.startswith('.'))
    if not dirs:
        sys.exit(f"错误: 目录下无子目录: {root_dir}")
    out_info = f" -> {output_dir}" if output_dir else " (输出到各物种目录下)"
    print(f"根目录: {root_dir}\n发现 {len(dirs)} 个物种{out_info}")
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    success = sum(1 for name in dirs
                  if process_species(os.path.join(root_dir, name), name, output_dir, output_fmt, force))
    print(f"\n完成: 成功 {success}/{len(dirs)}")


# ========== 帮助与入口 ==========

def show_help():
    script = os.path.basename(sys.argv[0])
    print(f"""
用法: python {script} [-i 输入] [-o 输出] [-s 物种] [-f 格式] [-h]

模式:
  批量 (默认)  python {script} [-i 根目录] [-o 输出根目录] [-f xlsx]
  单物种       python {script} -i 注释文件 基因组文件 -o 输出路径 -s 物种名 [-f csv]

参数:
  -i  输入路径。批量: 根目录(默认{DEFAULT_INPUT_DIR})；单物种: 注释+基因组两个文件
  -o  输出路径。批量: 输出根目录(可选)；单物种: 输出文件/目录(必填)
  -s  物种名称 (单物种必填，批量自动取目录名)
  -f  输出格式: xlsx (默认), tsv, csv
  -h  显示此帮助

支持格式:
  注释: .bed > .gff > .gff3 > .gbff    基因组: .fna > .fa > .fasta > .faa

输出:
  7列表格: gene_id | chromosome | start_position | end_position | strand | species | sequence

目录结构 (批量模式):
  根目录/SpeciesName/SpeciesName_annotation.gff + SpeciesName_genome.fna
  输出: 各物种目录下 SpeciesName_coordinates.xlsx (或其他指定格式)
""")


def main():
    if '-h' in sys.argv or '--help' in sys.argv:
        show_help()
        sys.exit(0)

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-i', '--input', nargs='+')
    parser.add_argument('-o', '--output')
    parser.add_argument('-s', '--species', default='Unknown')
    parser.add_argument('-f', '--format', default=DEFAULT_OUTPUT_FORMAT,
                        choices=['xlsx', 'tsv', 'csv'],
                        help=f'输出格式 (默认: {DEFAULT_OUTPUT_FORMAT})')
    parser.add_argument('-F', '--force', action='store_true')
    args = parser.parse_args()

    # 单物种模式: -i 传入2个文件
    if args.input and len(args.input) == 2 and os.path.isfile(args.input[0]) and os.path.isfile(args.input[1]):
        if not args.output:
            sys.exit("错误: 单物种模式需要 -o")
        if args.species == 'Unknown':
            sys.exit("错误: 单物种模式需要 -s")
        out = args.output
        if out.endswith(os.sep) or os.path.isdir(out):
            out = os.path.join(out, f"{args.species}_coordinates.{args.format}")
        for f, t in [(args.input[0], '注释'), (args.input[1], '基因组')]:
            if not os.path.isfile(f):
                sys.exit(f"错误: {t}文件不存在: {f}")
        print(f"物种: {args.species}\n注释: {args.input[0]}\n基因组: {args.input[1]}\n输出: {out}\n")
        # 直接执行三步流程
        genes = prepare_bed(args.input[0], args.force)
        if genes:
            fasta = prepare_fasta(genes, args.input[1], args.force)
            if fasta:
                merge_to_output(genes, fasta, out, args.species, args.format)

    # 批量模式
    else:
        if args.input and len(args.input) != 1:
            sys.exit("错误: 批量 -i 需1个目录; 单物种 -i 需2个文件")
        batch_process(args.input[0] if args.input else DEFAULT_INPUT_DIR,
                      args.output, args.format, args.force)


if __name__ == "__main__":
    main()
