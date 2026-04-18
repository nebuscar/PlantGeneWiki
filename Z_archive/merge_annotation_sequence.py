#!/usr/bin/env python3
"""
<<<<<<< HEAD
merge_annotation_sequence.py - 合并基因注释文件和基因组序列文件，生成TSV基因表格

流程: GFF->BED -> FNA->FASTA -> BED+FASTA->TSV
输出: gene_id | chromosome | start_position | end_position | strand | species | genome

用法:
  单物种: python merge_annotation_sequence.py -i <注释文件> <基因组文件> -o <输出路径> -s <物种名>
  批量:   python merge_annotation_sequence.py -d <根目录>

详细帮助: python merge_annotation_sequence.py -h
=======
merge_annotation_sequence.py - 合并注释文件和基因组文件，生成TSV基因表格

流程:
  1. GFF/GFF3 -> BED (坐标转换: 1-based closed -> 0-based half-open)
  2. FNA/FA   -> FASTA (按BED坐标提取序列，负链反向互补，序列大写)
  3. BED + FASTA -> TSV (七列输出)

输出TSV七列:
  gene_id | chromosome | start_position | end_position | strand | species | genome
  genome列格式: >gene_id::chrom:start-end\\nSEQUENCE (全大写)

用法:
  python merge_annotation_sequence.py -i <注释文件> <基因组文件> -o <输出路径> -s <物种名>

示例:
  python merge_annotation_sequence.py -i anno.gff genome.fna -o result.tsv -s Acer_yangbiense
  python merge_annotation_sequence.py -i anno.bed genome.fna -o /data/Acer_saccharum/ -s Acer_saccharum
>>>>>>> nizhu
"""

import sys
import os
<<<<<<< HEAD
import glob
import argparse
from Bio import SeqIO

_RC = str.maketrans('ATCGatcg', 'TAGCtagc')


def reverse_complement(seq):
    """DNA反向互补"""
    return seq.translate(_RC)[::-1]


def parse_bed(bed_file):
    """解析BED文件 -> [(gene_id, chrom, start, end, strand), ...]，重复ID只保留首条"""
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


def convert_gff_to_bed(gff_file, bed_file):
    """GFF/GFF3 -> BED (1-based closed -> 0-based half-open)，只提取gene/CDS"""
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


def extract_genes_from_fna(genes, fna_file, output_fasta):
    """按BED坐标从FNA提取基因序列，负链反向互补，序列大写"""
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
            out.write(f">{gid}::{chrom}:{start}-{end}\n{seq.upper()}\n")
            extracted += 1
    msg = f"    FNA->FASTA: {extracted} genes"
    if missing:
        msg += f", {len(missing)} chrom未匹配"
    print(msg)


def merge_to_tsv(genes, fasta_file, output_file, species):
    """BED+FASTA -> TSV (7列: gene_id, chromosome, start_position, end_position, strand, species, genome)"""
    gene_info = {g[0]: g[1:] for g in genes}
    matched = 0
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    with open(output_file, 'w') as out:
        out.write("gene_id\tchromosome\tstart_position\tend_position\tstrand\tspecies\tgenome\n")
        for record in SeqIO.parse(fasta_file, "fasta"):
            gid = record.id.split('::')[0]
            if gid in gene_info:
                chrom, start, end, strand = gene_info[gid]
                out.write(f'{gid}\t{chrom}\t{start}\t{end}\t{strand}\t{species}\t">{record.id}\n{str(record.seq)}\n')
                matched += 1
    print(f"    合并完成: {matched} genes -> {output_file}")


def need_rebuild(target, source):
    """目标文件不存在或源文件更新时返回True"""
    return not os.path.exists(target) or os.path.getmtime(target) < os.path.getmtime(source)


def find_file(directory, patterns):
    """按glob模式在目录中查找文件，返回首个匹配或None"""
    for p in patterns:
        matches = glob.glob(os.path.join(directory, p))
        if matches:
            return matches[0]
    return None


def prepare_bed_and_genes(ann_file):
    """根据注释文件类型准备基因列表 (.bed直接解析, .gff/.gff3先转BED)"""
    ext = os.path.splitext(ann_file)[1].lower()
    if ext == '.bed':
        return parse_bed(ann_file)
    if ext in ('.gff', '.gff3'):
        bed_file = os.path.splitext(ann_file)[0] + '.bed'
        if need_rebuild(bed_file, ann_file):
            convert_gff_to_bed(ann_file, bed_file)
        return parse_bed(bed_file)
    print(f"    错误: 不支持的注释格式 {ext}，需要 .bed/.gff/.gff3")
    return None


def prepare_fasta(genes, genome_file):
    """根据基因组文件类型准备FASTA (.fna/.fa提取序列, .fasta/.faa直接使用)"""
    ext = os.path.splitext(genome_file)[1].lower()
    if ext in ('.fna', '.fa'):
        fasta_file = os.path.splitext(genome_file)[0] + '_genes.fasta'
        if need_rebuild(fasta_file, genome_file):
            extract_genes_from_fna(genes, genome_file, fasta_file)
        return fasta_file
    if ext in ('.fasta', '.faa'):
        return genome_file
    print(f"    错误: 不支持的基因组格式 {ext}，需要 .fna/.fa/.fasta/.faa")
    return None


def run_pipeline(ann_file, genome_file, output_file, species):
    """完整处理流程: 注释->BED->基因列表, 基因组->FASTA, 合并->TSV"""
    genes = prepare_bed_and_genes(ann_file)
    if not genes:
        return False
    fasta_file = prepare_fasta(genes, genome_file)
    if not fasta_file:
        return False
    merge_to_tsv(genes, fasta_file, output_file, species)
    return True


def process_single(ann_file, genome_file, output_file, species):
    """单物种模式"""
    ann_file = os.path.abspath(ann_file)
    genome_file = os.path.abspath(genome_file)
    for fpath, label in [(ann_file, '注释'), (genome_file, '基因组')]:
        if not os.path.isfile(fpath):
            sys.exit(f"错误: {label}文件不存在: {fpath}")
    print(f"物种: {species}\n注释: {ann_file}\n基因组: {genome_file}\n输出: {output_file}\n")
    if not run_pipeline(ann_file, genome_file, output_file, species):
        sys.exit(1)


def process_species(species_dir, name):
    """批量模式: 处理单个物种子目录"""
    print(f"\n[{name}]")

    # 注释文件: BED优先, 其次GFF
    ann = find_file(species_dir, [f'{name}_annotation.bed'])
    if not ann:
        ann = find_file(species_dir, [f'{name}_annotation.gff', f'{name}_annotation.gff3'])
    if not ann:
        print("  跳过: 无注释文件")
        return False

    # 基因组文件: FNA优先, 其次FASTA/FAA
    genome = find_file(species_dir, [f'{name}_genome.fna', f'{name}_genome.fa'])
    if not genome:
        genome = find_file(species_dir, [f'{name}_genes.fasta', f'{name}_genes.fa', f'{name}_protein.faa'])
    if not genome:
        print("  跳过: 无基因组文件")
        return False

    print(f"  注释: {os.path.basename(ann)}  基因组: {os.path.basename(genome)}")
    return run_pipeline(ann, genome, os.path.join(species_dir, f"{name}_merged.tsv"), name)


def batch_process(root_dir):
    """批量模式: 遍历根目录下所有物种子目录"""
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
=======
import argparse
from Bio import SeqIO


def reverse_complement(seq):
    """DNA反向互补，非标准碱基保持原样"""
    comp = str.maketrans('ATCGatcg', 'TAGCtagc')
    return seq.translate(comp)[::-1]


def parse_bed(bed_file):
    """解析BED文件，返回 {gene_id: {chromosome, start, end, strand}}"""
    gene_info = {}
    dup_count = 0
    with open(bed_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) < 6:
                continue
            gene_id = parts[3]
            if gene_id in gene_info:
                dup_count += 1
            gene_info[gene_id] = {
                'chromosome': parts[0],
                'start': parts[1],
                'end': parts[2],
                'strand': parts[5]
            }
    if dup_count:
        print(f"  注意: {dup_count} 个重复gene_id，后者覆盖前者")
    return gene_info


def convert_gff_to_bed(gff_file, bed_file):
    """GFF/GFF3转BED: 1-based closed -> 0-based half-open"""
    print(f"[1/3] GFF -> BED: {gff_file}")
    gene_count = 0
    with open(gff_file, 'r') as fin, open(bed_file, 'w') as fout:
        for line in fin:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) < 9 or parts[2] not in ('gene', 'CDS'):
                continue

            chrom = parts[0]
            start = int(parts[3]) - 1  # 1-based -> 0-based
            end = parts[4]
            strand = parts[6]
            attrs = parts[8]

            gene_id = None
            if 'ID=' in attrs:
                gene_id = attrs.split('ID=', 1)[1].split(';', 1)[0].split(':', 1)[0]
            elif 'Name=' in attrs:
                gene_id = attrs.split('Name=', 1)[1].split(';', 1)[0]

            if gene_id:
                fout.write(f"{chrom}\t{start}\t{end}\t{gene_id}\t.\t{strand}\n")
                gene_count += 1

    print(f"  转换完成: {gene_count} 个基因")
    return bed_file


def extract_genes_from_fna(bed_file, fna_file, output_fasta):
    """从基因组FNA中按BED坐标提取基因序列，生成FASTA"""
    print(f"[2/3] FNA -> FASTA: {fna_file}")

    # 解析BED坐标
    genes = []
    with open(bed_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) < 6:
                continue
            genes.append({
                'chrom': parts[0],
                'start': int(parts[1]),
                'end': int(parts[2]),
                'gene_id': parts[3],
                'strand': parts[5]
            })
    print(f"  BED基因数: {len(genes)}")

    # 加载基因组
    genome = {}
    for record in SeqIO.parse(fna_file, "fasta"):
        genome[record.id] = str(record.seq)
    print(f"  染色体/contig数: {len(genome)}")

    # 提取序列
    extracted = 0
    missing_chroms = set()
    with open(output_fasta, 'w') as out:
        for gene in genes:
            chrom = gene['chrom']
            if chrom not in genome:
                missing_chroms.add(chrom)
                continue

            seq = genome[chrom][gene['start']:gene['end']]
            if gene['strand'] == '-':
                seq = reverse_complement(seq)
            seq = seq.upper()

            out.write(f">{gene['gene_id']}::{chrom}:{gene['start']}-{gene['end']}\n{seq}\n")
            extracted += 1

    print(f"  提取完成: {extracted} 个基因")
    if missing_chroms:
        print(f"  警告: {len(missing_chroms)} 条染色体未匹配: {list(missing_chroms)}")
    return output_fasta


def merge_to_tsv(bed_file, fasta_file, output_file, species):
    """合并BED注释和FASTA序列，输出TSV"""
    print(f"[3/3] 合并 -> TSV: {output_file}")

    gene_info = parse_bed(bed_file)
    print(f"  BED注释数: {len(gene_info)}")

    # 确保输出目录存在
    out_dir = os.path.dirname(output_file)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    matched = 0
    unmatched = 0
    with open(output_file, 'w') as out:
        out.write("gene_id\tchromosome\tstart_position\tend_position\tstrand\tspecies\tgenome\n")

        for record in SeqIO.parse(fasta_file, "fasta"):
            gene_id = record.id.split('::')[0]
            sequence = str(record.seq)

            if gene_id in gene_info:
                info = gene_info[gene_id]
                fasta_str = f">{record.id}\n{sequence}"
                out.write(f"{gene_id}\t{info['chromosome']}\t{info['start']}\t{info['end']}\t{info['strand']}\t{species}\t{fasta_str}\n")
                matched += 1
            else:
                unmatched += 1

    print(f"  完成: 匹配 {matched} 个基因" + (f"，未匹配 {unmatched} 个" if unmatched else ""))
    print(f"  输出: {output_file}")


def resolve_output_path(output_arg, species):
    """解析输出路径: 文件路径直接用，目录路径自动生成文件名"""
    if output_arg.endswith(os.sep) or os.path.isdir(output_arg):
        if species == 'Unknown':
            print("错误: 输出为目录时必须指定物种名 (-s)")
            sys.exit(1)
        return os.path.join(output_arg, f"{species}_merged.tsv")
    return output_arg


def get_derived_path(input_file, new_ext):
    """基于输入文件路径生成派生文件路径(同目录，换扩展名)"""
    base, _ = os.path.splitext(input_file)
    return base + new_ext
>>>>>>> nizhu


def main():
    parser = argparse.ArgumentParser(
<<<<<<< HEAD
        prog='merge_annotation_sequence.py',
        description='合并基因注释文件和基因组序列文件，生成TSV表格',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
运行模式 (二选一):
  单物种: python %(prog)s -i <注释文件> <基因组文件> -o <输出路径> -s <物种名>
  批量:   python %(prog)s -d <根目录>

支持格式:
  注释文件:  .bed (优先), .gff, .gff3
  基因组文件: .fna, .fa (优先), .fasta, .faa

输出路径 (-o):
  文件路径: 直接指定         如 -o result.tsv
  目录路径: 自动拼接文件名   如 -o /data/output/ (需配合 -s)

批量模式目录结构:
  root_dir/SpeciesName/{SpeciesName}_annotation.gff|.bed + {SpeciesName}_genome.fna
  自动规则: 物种名=目录名, BED优先GFF, FNA优先FASTA, 输出到子目录下

示例:
  # 单物种 - 输出到文件
  python %(prog)s -i anno.gff genome.fna -o result.tsv -s Acer_yangbiense

  # 单物种 - 输出到目录 (自动命名为 Acer_negundo_merged.tsv)
  python %(prog)s -i anno.bed genes.fasta -o /output/ -s Acer_negundo

  # 批量 - 遍历根目录下所有物种
  python %(prog)s -d /path/to/genomes/
""")

    parser.add_argument('-i', '--input', nargs=2, metavar=('ANNOTATION', 'GENOME'),
                        help='单物种模式: 注释文件(BED/GFF/GFF3) + 基因组文件(FNA/FA/FASTA/FAA)')
    parser.add_argument('-o', '--output', metavar='PATH',
                        help='单物种模式: 输出路径 (文件或目录，目录时需 -s)')
    parser.add_argument('-s', '--species', default='Unknown', metavar='NAME',
                        help='单物种模式: 物种名称 (输出为目录时必填)')
    parser.add_argument('-d', '--directory', metavar='DIR',
                        help='批量模式: 根目录路径，自动遍历物种子目录')

    args = parser.parse_args()

    if args.directory:
        if args.input:
            parser.error("-d 和 -i 不可同时使用")
        batch_process(args.directory)
    elif args.input:
        if not args.output:
            parser.error("单物种模式需要 -o 指定输出路径")
        # 解析输出路径: 目录则自动拼接文件名
        output_file = args.output
        if output_file.endswith(os.sep) or os.path.isdir(output_file):
            if args.species == 'Unknown':
                parser.error("输出为目录时必须指定 -s 物种名")
            output_file = os.path.join(output_file, f"{args.species}_merged.tsv")
        process_single(args.input[0], args.input[1], output_file, args.species)
    else:
        parser.error("请使用 -i (单物种) 或 -d (批量) 指定输入，-h 查看帮助")
=======
        description='合并基因注释文件和基因组序列文件，生成TSV表格',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
支持的输入格式:
  注释文件: .bed, .gff, .gff3
  基因组文件: .fna, .fa, .fasta, .faa

输出路径 (-o):
  文件路径: 直接指定输出文件  如 -o result.tsv
  目录路径: 自动生成文件名    如 -o /data/Acer_yangbiense/
       自动生成: /data/Acer_yangbiense/Acer_yangbiense_merged.tsv

示例:
  python %(prog)s -i anno.gff genome.fna -o result.tsv -s Acer_yangbiense
  python %(prog)s -i anno.bed genome.fna -o /data/Acer_saccharum/ -s Acer_saccharum
  python %(prog)s -i anno.bed genes.fasta -o result.tsv -s Acer_negundo
""")
    parser.add_argument('-i', '--input', nargs=2, metavar=('ANNOTATION', 'GENOME'),
                        help='注释文件(BED/GFF/GFF3) + 基因组文件(FNA/FA/FASTA/FAA)')
    parser.add_argument('-o', '--output', required=True, metavar='PATH',
                        help='输出路径: 文件路径或目录路径')
    parser.add_argument('-s', '--species', default='Unknown',
                        help='物种名称 (输出为目录时必填)')

    args = parser.parse_args()

    if not args.input:
        parser.error("缺少输入文件，请使用 -i 指定注释文件和基因组文件")

    annotation_file = os.path.abspath(args.input[0])
    genome_file = os.path.abspath(args.input[1])
    species = args.species
    output_file = resolve_output_path(args.output, species)

    # 校验输入文件
    if not os.path.isfile(annotation_file):
        parser.error(f"注释文件不存在: {annotation_file}")
    if not os.path.isfile(genome_file):
        parser.error(f"基因组文件不存在: {genome_file}")

    ext_ann = os.path.splitext(annotation_file)[1].lower()
    ext_genome = os.path.splitext(genome_file)[1].lower()

    print(f"输入: {annotation_file} ({ext_ann}) + {genome_file} ({ext_genome})")
    print(f"输出: {output_file}")
    print(f"物种: {species}\n")

    # ---- 步骤1: 注释文件 -> BED ----
    if ext_ann in ('.gff', '.gff3'):
        bed_file = get_derived_path(annotation_file, '.bed')
        if not os.path.exists(bed_file) or os.path.getmtime(bed_file) < os.path.getmtime(annotation_file):
            convert_gff_to_bed(annotation_file, bed_file)
        else:
            print(f"[1/3] 使用已有BED: {bed_file}")
    elif ext_ann == '.bed':
        bed_file = annotation_file
        print(f"[1/3] BED文件: {bed_file}")
    else:
        parser.error(f"不支持的注释格式 {ext_ann}，需要 .bed/.gff/.gff3")

    # ---- 步骤2: 基因组文件 -> FASTA ----
    if ext_genome in ('.fna', '.fa'):
        fasta_file = get_derived_path(genome_file, '_genes.fasta')
        if not os.path.exists(fasta_file) or os.path.getmtime(fasta_file) < os.path.getmtime(genome_file):
            extract_genes_from_fna(bed_file, genome_file, fasta_file)
        else:
            print(f"[2/3] 使用已有FASTA: {fasta_file}")
    elif ext_genome in ('.fasta', '.faa'):
        fasta_file = genome_file
        print(f"[2/3] FASTA文件: {fasta_file}")
    else:
        parser.error(f"不支持的基因组格式 {ext_genome}，需要 .fna/.fa/.fasta/.faa")

    # ---- 步骤3: 合并 -> TSV ----
    merge_to_tsv(bed_file, fasta_file, output_file, species)

    print("\n完成!")
>>>>>>> nizhu


if __name__ == "__main__":
    main()
