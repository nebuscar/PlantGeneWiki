#!/usr/bin/env python3
"""
merge_annotation_sequence.py - 批量合并注释与基因组文件，生成TSV基因表格

流程: GFF->BED -> FNA->FASTA -> BED+FASTA->TSV
输出: gene_id | chromosome | start_position | end_position | strand | species | genome

用法:
  python merge_annotation_sequence.py -d /path/to/genomes/

目录结构:
  root_dir/SpeciesName/{SpeciesName}_annotation.gff|.bed + {SpeciesName}_genome.fna
自动规则: 物种名=目录名, BED优先GFF, FNA优先FASTA, 输出到子目录下
"""

import sys
import os
import glob
import argparse
from Bio import SeqIO

_RC = str.maketrans('ATCGatcg', 'TAGCtagc')


def reverse_complement(seq):
    return seq.translate(_RC)[::-1]


def parse_bed(bed_file):
    """解析BED -> [(gene_id, chrom, start, end, strand), ...]"""
    genes = []
    seen = set()
    with open(bed_file) as f:
        for line in f:
            parts = line.split('\t')
            if len(parts) < 6 or parts[3].startswith('#'):
                continue
            gid = parts[3]
            if gid in seen:
                continue
            seen.add(gid)
            genes.append((gid, parts[0], int(parts[1]), int(parts[2]), parts[5]))
    return genes


def convert_gff_to_bed(gff_file, bed_file):
    """GFF/GFF3 -> BED (1-based closed -> 0-based half-open)"""
    count = 0
    with open(gff_file) as fin, open(bed_file, 'w') as fout:
        for line in fin:
            parts = line.split('\t')
            if len(parts) < 9 or parts[2] not in ('gene', 'CDS'):
                continue
            attrs = parts[8]
            gid = None
            if 'ID=' in attrs:
                gid = attrs.split('ID=', 1)[1].split(';', 1)[0].split(':', 1)[0]
            elif 'Name=' in attrs:
                gid = attrs.split('Name=', 1)[1].split(';', 1)[0]
            if gid:
                fout.write(f"{parts[0]}\t{int(parts[3]) - 1}\t{parts[4]}\t{gid}\t.\t{parts[6]}\n")
                count += 1
    print(f"    GFF->BED: {count} genes")
    return bed_file


def extract_genes_from_fna(genes, fna_file, output_fasta):
    """按BED坐标从FNA提取基因序列，负链反向互补，序列大写"""
    genome = {}
    for record in SeqIO.parse(fna_file, "fasta"):
        genome[record.id] = str(record.seq)

    extracted = 0
    missing = set()
    with open(output_fasta, 'w') as out:
        for gid, chrom, start, end, strand in genes:
            if chrom not in genome:
                missing.add(chrom)
                continue
            seq = genome[chrom][start:end]
            if strand == '-':
                seq = reverse_complement(seq)
            out.write(f">{gid}::{chrom}:{start}-{end}\n{seq.upper()}\n")
            extracted += 1
    msg = f"    FNA->FASTA: {extracted} genes"
    if missing:
        msg += f", {len(missing)} chrom未匹配"
    print(msg)
    return output_fasta


def merge_to_tsv(genes, fasta_file, output_file, species):
    """BED+FASTA -> TSV"""
    gene_info = {g[0]: g[1:] for g in genes}
    matched = 0
    with open(output_file, 'w') as out:
        out.write("gene_id\tchromosome\tstart_position\tend_position\tstrand\tspecies\tgenome\n")
        for record in SeqIO.parse(fasta_file, "fasta"):
            gid = record.id.split('::')[0]
            if gid in gene_info:
                chrom, start, end, strand = gene_info[gid]
                out.write(f'{gid}\t{chrom}\t{start}\t{end}\t{strand}\t{species}\t">{record.id}\n{str(record.seq)}\n')
                matched += 1
    print(f"    合并完成: {matched} genes -> {output_file}")


def find_file(directory, patterns):
    for p in patterns:
        matches = glob.glob(os.path.join(directory, p))
        if matches:
            return matches[0]
    return None


def need_rebuild(target, source):
    return not os.path.exists(target) or os.path.getmtime(target) < os.path.getmtime(source)


def process_species(species_dir, name):
    """处理单个物种"""
    print(f"\n[{name}]")

    # 查找注释文件: BED优先, 其次GFF
    ann = find_file(species_dir, [f'{name}_annotation.bed'])
    is_gff = False
    if not ann:
        ann = find_file(species_dir, [f'{name}_annotation.gff', f'{name}_annotation.gff3'])
        is_gff = True
    if not ann:
        print("  跳过: 无注释文件")
        return False

    # 查找基因组文件: FNA优先, 其次FASTA
    genome = find_file(species_dir, [f'{name}_genome.fna', f'{name}_genome.fa'])
    is_fna = True
    if not genome:
        genome = find_file(species_dir, [f'{name}_genes.fasta', f'{name}_genes.fa', f'{name}_protein.faa'])
        is_fna = False
    if not genome:
        print("  跳过: 无基因组文件")
        return False

    print(f"  注释: {os.path.basename(ann)}  基因组: {os.path.basename(genome)}")

    # GFF -> BED
    if is_gff:
        bed_file = os.path.splitext(ann)[0] + '.bed'
        if need_rebuild(bed_file, ann):
            convert_gff_to_bed(ann, bed_file)
    else:
        bed_file = ann

    genes = parse_bed(bed_file)

    # FNA -> FASTA
    if is_fna:
        fasta_file = os.path.splitext(genome)[0] + '_genes.fasta'
        if need_rebuild(fasta_file, genome):
            extract_genes_from_fna(genes, genome, fasta_file)
    else:
        fasta_file = genome

    # 合并 -> TSV
    output_file = os.path.join(species_dir, f"{name}_merged.tsv")
    merge_to_tsv(genes, fasta_file, output_file, name)
    return True


def batch_process(root_dir):
    """批量处理根目录下所有物种子目录"""
    root_dir = os.path.abspath(root_dir)
    if not os.path.isdir(root_dir):
        sys.exit(f"错误: 目录不存在: {root_dir}")

    dirs = sorted(d for d in os.listdir(root_dir)
                  if os.path.isdir(os.path.join(root_dir, d)) and not d.startswith('.'))
    if not dirs:
        sys.exit(f"错误: 目录下无子目录: {root_dir}")

    print(f"根目录: {root_dir}\n发现 {len(dirs)} 个物种")

    success = sum(1 for name in dirs if process_species(os.path.join(root_dir, name), name))
    print(f"\n完成: 成功 {success}/{len(dirs)}")


def main():
    parser = argparse.ArgumentParser(
        description='批量合并基因注释和基因组序列文件，生成TSV表格',
        epilog='示例: python %(prog)s -d /path/to/genomes/')
    parser.add_argument('-d', '--directory', required=True, metavar='DIR',
                        help='根目录路径，自动遍历所有物种子目录')
    batch_process(parser.parse_args().directory)


if __name__ == "__main__":
    main()
  