#!/usr/bin/env python3
"""
合并注释文件和基因组文件，生成TSV格式的基因表格
支持GFF转BED和FNA提取基因序列
输出格式：gene_id, chromosome, start_position, end_position, strand, species, genome
"""

import sys
import os
from Bio import SeqIO


def reverse_complement(dna_sequence):
    complement = {
        "A": "T",
        "T": "A",
        "C": "G",
        "G": "C",
        "a": "t",
        "t": "a",
        "c": "g",
        "g": "c",
        "N": "N",
        "n": "n",
    }
    return "".join([complement[base] for base in dna_sequence[::-1]])


def parse_bed(bed_file):
    gene_info = {}
    with open(bed_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or len(line.split("\t")) < 6:
                continue
            parts = line.split("\t")
            gene_info[parts[3]] = {
                "chromosome": parts[0],
                "start": parts[1],
                "end": parts[2],
                "strand": parts[5],
            }
    return gene_info


def convert_gff_to_bed(gff_file, bed_file):
    print(f"转换GFF到BED: {gff_file} -> {bed_file}")
    gene_count = 0
    with open(gff_file, "r") as gff, open(bed_file, "w") as bed:
        for line in gff:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 9 or parts[2] not in ["gene", "CDS"]:
                continue

            chrom = parts[0]
            start = int(parts[3]) - 1
            end = parts[4]
            strand = parts[6]
            attributes = parts[8]

            gene_id = None
            if "ID=" in attributes:
                gene_id = attributes.split("ID=")[1].split(";")[0].split(":")[0]
            elif "Name=" in attributes:
                gene_id = attributes.split("Name=")[1].split(";")[0]

            if gene_id:
                bed.write(f"{chrom}\t{start}\t{end}\t{gene_id}\t.\t{strand}\n")
                gene_count += 1

    print(f"完成转换，共 {gene_count} 个基因")
    return bed_file


def extract_genes_from_fna(bed_file, fna_file, output_fasta):
    print(f"从FNA提取基因序列: {fna_file} -> {output_fasta}")

    genes = []
    with open(bed_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or len(line.split("\t")) < 6:
                continue
            parts = line.split("\t")
            genes.append(
                {
                    "chromosome": parts[0],
                    "start": int(parts[1]),
                    "end": int(parts[2]),
                    "gene_id": parts[3],
                    "strand": parts[5],
                }
            )

    print(f"共 {len(genes)} 个基因")

    genome = {}
    for record in SeqIO.parse(fna_file, "fasta"):
        genome[record.id] = str(record.seq)
    print(f"加载 {len(genome)} 条染色体/contig")

    extracted = 0
    missing_chroms = set()

    with open(output_fasta, "w") as out:
        for gene in genes:
            chrom = gene["chromosome"]
            if chrom not in genome:
                missing_chroms.add(chrom)
                continue

            sequence = genome[chrom][gene["start"] : gene["end"]]

            if gene["strand"] == "-":
                sequence = reverse_complement(sequence)

            sequence = sequence.upper()
            out.write(
                f">{gene['gene_id']}::{chrom}:{gene['start']}-{gene['end']}\n{sequence}\n"
            )
            extracted += 1

    print(f"成功提取 {extracted} 个基因")
    if missing_chroms:
        print(f"未匹配的染色体/contig: {list(missing_chroms)}")

    return output_fasta


def merge_files(bed_file, fasta_file, output_file, species):
    print(f"合并文件: {bed_file} + {fasta_file} -> {output_file}")

    gene_info = parse_bed(bed_file)
    print(f"加载 {len(gene_info)} 个基因注释")

    matched_count = 0
    with open(output_file, "w") as out:
        out.write(
            "gene_id\tchromosome\tstart_position\tend_position\tstrand\tspecies\tgenome\n"
        )

        for record in SeqIO.parse(fasta_file, "fasta"):
            gene_id_full = record.id
            gene_id = gene_id_full.split("::")[0]
            sequence = str(record.seq)

            if gene_id in gene_info:
                info = gene_info[gene_id]
                fasta_format = f">{gene_id_full}\n{sequence}"
                out.write(
                    f"{gene_id}\t{info['chromosome']}\t{info['start']}\t{info['end']}\t{info['strand']}\t{species}\t{fasta_format}\n"
                )
                matched_count += 1

    print(f"完成合并，成功匹配 {matched_count} 个基因")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(
            "用法: python merge_annotation_sequence.py <注释文件> <基因组文件> <输出文件> [物种名]"
        )
        print("支持格式: BED + FASTA, GFF + FNA (自动转换), BED + FNA, GFF + FASTA")
        sys.exit(1)

    annotation_file = sys.argv[1]
    genome_file = sys.argv[2]
    output_file = sys.argv[3]
    species = sys.argv[4] if len(sys.argv) > 4 else "Unknown"

    ext_ann = os.path.splitext(annotation_file)[1].lower()
    ext_genome = os.path.splitext(genome_file)[1].lower()

    print(f"\n输入: {annotation_file} ({ext_ann}) + {genome_file} ({ext_genome})")
    print(f"输出: {output_file}")
    print(f"物种: {species}\n")

    bed_file = None
    fasta_file = None

    if ext_ann in [".gff", ".gff3"]:
        bed_file = annotation_file.replace(".gff", ".bed").replace(".gff3", ".bed")
        if not os.path.exists(bed_file) or os.path.getmtime(
            bed_file
        ) < os.path.getmtime(annotation_file):
            convert_gff_to_bed(annotation_file, bed_file)
        else:
            print(f"使用已存在的BED文件: {bed_file}")
    elif ext_ann == ".bed":
        bed_file = annotation_file
    else:
        print(f"错误: 不支持的注释文件格式 {ext_ann}")
        sys.exit(1)

    if ext_genome in [".fna", ".fa"]:
        base_name = genome_file.rsplit(f".{ext_genome[1:]}", 1)[0]
        fasta_file = f"{base_name}_genes.fasta"
        if not os.path.exists(fasta_file) or os.path.getmtime(
            fasta_file
        ) < os.path.getmtime(genome_file):
            extract_genes_from_fna(bed_file, genome_file, fasta_file)
        else:
            print(f"使用已存在的FASTA文件: {fasta_file}")
    elif ext_genome in [".fasta", ".faa"]:
        fasta_file = genome_file
    else:
        print(f"错误: 不支持的基因组文件格式 {ext_genome}")
        sys.exit(1)

    merge_files(bed_file, fasta_file, output_file, species)
