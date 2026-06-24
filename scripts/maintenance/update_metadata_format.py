#!/usr/bin/env python3
"""
更新 metadata.yaml 为结构化格式
"""

import os
import re
from datetime import datetime


def parse_old_yaml(content):
    """解析旧的扁平 YAML 格式"""
    data = {}
    for line in content.split('\n'):
        line = line.strip()
        if ':' in line and not line.startswith('#'):
            parts = line.split(':', 1)
            key = parts[0].strip()
            value = parts[1].strip() if len(parts) > 1 else ''
            data[key] = value
    return data


def get_files_category(files):
    """根据文件名分类"""
    categories = {
        'assembly': [],
        'annotation': [],
        'analysis': [],
        'gene': []
    }

    for f in files:
        if 'genomic.fa' in f or 'genome.fa' in f:
            categories['assembly'].append(f)
        elif 'genomic.gff' in f or 'longest.gff' in f or 'repeat.gff' in f or 'cds.fa' in f or 'pep.fa' in f:
            categories['annotation'].append(f)
        elif 'interpro.gff' in f or 'mirna.gff' in f:
            categories['analysis'].append(f)
        elif 'gene.json' in f or 'gene.tsv' in f or 'gene.txt' in f:
            categories['gene'].append(f)
        else:
            categories['annotation'].append(f)

    return categories


def format_new_yaml(data, files):
    """生成新的结构化 YAML 格式"""
    species = data.get('species', '')
    common_name = data.get('Common_Name', '')
    ncbi_taxid = data.get('NCBI_TaxID', '')
    ncbi_taxonomy_id = data.get('ncbi_taxonomy_ID', '')

    # Taxonomy
    taxonomy = {
        'scientific_name': data.get('Scientific_Name', ''),
        'rank': data.get('Taxonomic_Rank', ''),
        'kingdom': data.get('Kingdom', ''),
        'phylum': data.get('Phylum', ''),
        'class': data.get('Class', ''),
        'order': data.get('Order', ''),
        'family': data.get('Family', ''),
        'genus': data.get('Genus', ''),
        'apg_iv': data.get('APG_IV', ''),
        'clade': data.get('Clade', '')
    }

    # Assembly
    assembly = {
        'level': data.get('assembly_level', ''),
        'accession_count': data.get('assem_num', ''),
        'total_length_bp': data.get('total_length', ''),
        'gene_count': data.get('gene_num', ''),
        'transcript_count': data.get('transcript_num', ''),
        'n50': data.get('n50', ''),
        'l50': data.get('l50', ''),
        'busco': data.get('busco', ''),
        'predicted_gene_number': data.get('Predicted_gene_number', '')
    }

    # Genome Size
    genome_size = {
        'assembled_mb': data.get('Assembled_genome_size_MB', ''),
        'estimated_mb': data.get('Estimated_genome_size_MB', ''),
        'contig_n50_kb': data.get('Contig_N50_size_KB', ''),
        'scaffold_n50_kb': data.get('Scaffold_N50_size_KB', '')
    }

    # Software
    software = {
        'acs_name': data.get('Acs_name', ''),
        'scaffolding': data.get('Software_of_scaffolding', ''),
        'contig_assembly': data.get('Software_of_contig_assembly', ''),
        'polishing': data.get('Software_of_polishing', ''),
        'hic_scaffolding': data.get('Software_of_HiC_scaffolding', '')
    }

    # Platform
    platform = {
        'sequencing': data.get('Sequencing_platform', ''),
        'classification': data.get('Platform_classification', ''),
        'country': data.get('Country_or_Institution', ''),
        'hic_used': data.get('If_use_HiC', '')
    }

    # Publication
    publication = {
        'title': data.get('Publication', ''),
        'year': data.get('Publish_year', ''),
        'pmid_doi': data.get('PMID_or_DOI', '')
    }

    # Files
    files_categories = get_files_category(files)

    # 构建新 YAML
    lines = []

    # Basic Info
    lines.append("# Basic Info")
    lines.append(f"species: {species}")
    if common_name:
        lines.append(f"common_name: {common_name}")
    lines.append(f"internal_version: {data.get('version', 'v1')}")
    if ncbi_taxid:
        lines.append(f"ncbi_taxid: {ncbi_taxid}")
    if ncbi_taxonomy_id:
        lines.append(f"ncbi_taxonomy_id: {ncbi_taxonomy_id}")
    lines.append(f"source: {data.get('source', 'PGCP')}")
    lines.append(f"created: {data.get('created', datetime.now().strftime('%Y-%m-%d'))}")

    # Taxonomy
    lines.append("")
    lines.append("# Taxonomy")
    lines.append("taxonomy:")
    for key, value in taxonomy.items():
        if value:
            lines.append(f"  {key}: {value}")

    # Data Sources
    lines.append("")
    lines.append("# Data Sources")
    lines.append("data_sources:")
    lines.append("  - name: PGCP")
    lines.append(f"    version: {data.get('version', 'v1')}")
    lines.append("    url: https://biobigdata.nju.edu.cn/pgdatabaseAPI/")
    if data.get('phytozome_ID'):
        lines.append(f"    accession: {data.get('phytozome_ID')}")
    if data.get('Spec_name'):
        lines.append(f"    spec_name: {data.get('Spec_name')}")
    lines.append(f"    access_date: {data.get('created', datetime.now().strftime('%Y-%m-%d'))}")

    # Assembly
    lines.append("")
    lines.append("# Assembly")
    lines.append("assembly:")
    for key, value in assembly.items():
        if value:
            lines.append(f"  {key}: {value}")

    # Genome Size
    lines.append("")
    lines.append("# Genome Size")
    lines.append("genome_size:")
    for key, value in genome_size.items():
        if value:
            lines.append(f"  {key}: {value}")

    # Ploidy
    if data.get('Ploidy'):
        lines.append("")
        lines.append("# Ploidy")
        lines.append(f"ploidy: {data.get('Ploidy')}")

    # Software
    lines.append("")
    lines.append("# Software")
    lines.append("software:")
    for key, value in software.items():
        if value and value != 'NA':
            lines.append(f"  {key}: {value}")

    # Platform
    lines.append("")
    lines.append("# Platform")
    lines.append("platform:")
    for key, value in platform.items():
        if value and value != 'NA':
            lines.append(f"  {key}: {value}")

    # Publication
    lines.append("")
    lines.append("# Publication")
    lines.append("publication:")
    for key, value in publication.items():
        if value:
            lines.append(f"  {key}: {value}")

    # Files
    lines.append("")
    lines.append("# Files")
    lines.append("files:")

    for category in ['assembly', 'annotation', 'analysis', 'gene']:
        if files_categories[category]:
            lines.append(f"  {category}:")
            for f in sorted(files_categories[category]):
                lines.append(f"    - {f}")

    return '\n'.join(lines)


def main():
    TARGET_BASE = "/DATA/data2/genomes"
    updated = 0

    for species in sorted(os.listdir(TARGET_BASE)):
        pgcp_dir = os.path.join(TARGET_BASE, species, "PGCP", "v1")
        if not os.path.isdir(pgcp_dir):
            continue

        metadata_path = os.path.join(pgcp_dir, "metadata.yaml")
        if not os.path.exists(metadata_path):
            continue

        # 读取旧格式
        with open(metadata_path, 'r') as f:
            old_content = f.read()

        # 解析
        data = parse_old_yaml(old_content)

        # 提取 files
        files = []
        in_files = False
        for line in old_content.split('\n'):
            if line.strip().startswith('files:'):
                in_files = True
                continue
            if in_files and line.strip().startswith('- '):
                files.append(line.strip().replace('- ', '').strip())
            elif in_files and line.strip() and not line.strip().startswith('-'):
                break

        # 生成新格式
        new_content = format_new_yaml(data, files)

        # 写回
        with open(metadata_path, 'w') as f:
            f.write(new_content)

        updated += 1

    print(f"Updated {updated} metadata.yaml files")


if __name__ == '__main__':
    main()