#!/usr/bin/env python3
"""
从PGCP API爬取完整的物种信息
使用方法: python crawl_pgcp_data.py [--output DIR]
"""

import urllib.request
import json
import time
import os
import argparse
from datetime import datetime

def crawl_pgcp_data():
    """从PGCP API爬取完整物种信息"""

    url = "https://biobigdata.nju.edu.cn/pgdatabaseAPI/navlist"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read())

    species_list = data.get('genome', [])
    print(f"Total species in PGCP: {len(species_list)}")

    full_data = {}
    errors = []

    for i, sp in enumerate(species_list):
        api_url = f"https://biobigdata.nju.edu.cn/pgdatabaseAPI/genome?species={sp}"
        try:
            req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=30)
            sp_data = json.loads(resp.read())

            tools = sp_data.get('species', {}).get('tools', {})
            assembly = sp_data.get('species', {}).get('assembly', {}).get('v1', {})

            full_data[sp] = {
                # Basic info
                'full_name': sp_data.get('species', {}).get('full_name', ''),
                'ncbi_taxonomy_ID': sp_data.get('species', {}).get('ncbi_taxonomy_ID', ''),
                'phytozome_ID': sp_data.get('species', {}).get('phytozome_ID', ''),
                'name': sp_data.get('species', {}).get('name', ''),

                # Taxonomy from tools
                'Spec_name': tools.get('Spec_name', ''),
                'Publication': tools.get('Publication', ''),
                'Publish_year': tools.get('Publish_year', ''),
                'PMID_or_DOI': tools.get('PMID_or_DOI', ''),
                'Order': tools.get('Order', ''),
                'Family': tools.get('Family', ''),
                'Clade': tools.get('Clade', ''),
                'APG_IV': tools.get('APG_IV', ''),

                # Genome info
                'Acs_name': tools.get('Acs_name', ''),
                'Ploidy': tools.get('Ploidy', ''),
                'Predicted_gene_number': tools.get('Predicted_gene_number', ''),

                # Software
                'Software_of_scaffolding': tools.get('Software_of_scaffolding', ''),
                'Software_of_contig_assembly': tools.get('Software_of_contig_assembly', ''),
                'Software_of_polishing': tools.get('Software_of_polishing', ''),
                'Software_of_HiC_scaffolding': tools.get('Software_of_HiC_scaffolding', ''),

                # Size info
                'Assembled_genome_size_MB': tools.get('Assembled_genome_size_MB', ''),
                'Estimated_genome_size_MB': tools.get('Estimated_genome_size_MB', ''),
                'Contig_N50_size_KB': tools.get('Contig_N50_size_KB', ''),
                'Scaffold_N50_size_KB': tools.get('Scaffold_N50_size_KB', ''),

                # Platform
                'Sequencing_platform': tools.get('Sequencing_platform', ''),
                'Platform_classification': tools.get('Platform_classification', ''),
                'Country_or_Institution': tools.get('Country_or_Institution', ''),
                'If_use_HiC': tools.get('If_use_HiC', ''),

                # Assembly data
                'assembly_level': assembly.get('assem_level', ''),
                'assem_num': assembly.get('assem_num', ''),
                'total_length': assembly.get('total_length', ''),
                'gene_num': assembly.get('gene_num', ''),
                'transcript_num': assembly.get('transcript_num', ''),
                'n50': assembly.get('N50', ''),
                'l50': assembly.get('L50', ''),
                'busco': assembly.get('busco_eukaryote', ''),
            }

            if (i + 1) % 100 == 0:
                print(f"Progress: {i+1}/{len(species_list)}")

        except Exception as e:
            errors.append((sp, str(e)))

        time.sleep(0.2)

    print(f"\nCrawled {len(full_data)} species assembly info")
    print(f"Errors: {len(errors)}")
    if errors:
        print(f"First 5 errors: {errors[:5]}")

    return full_data

def update_metadata_yaml(base_dir, full_data, species_taxonomy=None):
    """更新所有metadata.yaml文件"""

    updated = 0

    for species_dir in os.listdir(base_dir):
        pgcp_dir = os.path.join(base_dir, species_dir, 'PGCP', 'v1')
        metadata_path = os.path.join(pgcp_dir, 'metadata.yaml')

        if os.path.isdir(pgcp_dir):
            key = species_dir.strip().lower().replace(' ', '_')
            dir_key = species_dir.strip().lower()

            # Get files
            files = sorted([f for f in os.listdir(pgcp_dir) if f != 'metadata.yaml'])

            # Build metadata
            metadata = f"species: {key}\nversion: v1\nsource: PGCP\ncreated: {datetime.now().strftime('%Y-%m-%d')}\n"

            # Add taxonomy info from species_list
            if species_taxonomy and dir_key in species_taxonomy:
                tax = species_taxonomy[dir_key]
                for field in ['Scientific_Name', 'NCBI_TaxID', 'Taxonomic_Rank', 'Kingdom', 'Phylum', 'Class', 'Order', 'Family', 'Genus', 'Common_Name']:
                    val = tax.get(field)
                    if val:
                        metadata += f"{field}: {val}\n"

            # Add other fields from PGCP data
            if key in full_data:
                data = full_data[key]

                # Taxonomy IDs
                if data.get('ncbi_taxonomy_ID'):
                    metadata += f"ncbi_taxonomy_ID: {data['ncbi_taxonomy_ID']}\n"
                if data.get('phytozome_ID'):
                    metadata += f"phytozome_ID: {data['phytozome_ID']}\n"
                if data.get('Spec_name'):
                    metadata += f"Spec_name: {data['Spec_name']}\n"

                # Taxonomy
                if data.get('APG_IV'):
                    metadata += f"APG_IV: {data['APG_IV']}\n"
                if data.get('Clade'):
                    metadata += f"Clade: {data['Clade']}\n"
                if data.get('Ploidy'):
                    metadata += f"Ploidy: {data['Ploidy']}\n"
                if data.get('Predicted_gene_number'):
                    metadata += f"Predicted_gene_number: {data['Predicted_gene_number']}\n"

                # Assembly
                if data.get('assembly_level'):
                    metadata += f"assembly_level: {data['assembly_level']}\n"
                if data.get('assem_num'):
                    metadata += f"assem_num: {data['assem_num']}\n"
                if data.get('total_length'):
                    metadata += f"total_length: {data['total_length']}\n"
                if data.get('gene_num'):
                    metadata += f"gene_num: {data['gene_num']}\n"
                if data.get('transcript_num'):
                    metadata += f"transcript_num: {data['transcript_num']}\n"
                if data.get('n50'):
                    metadata += f"n50: {data['n50']}\n"
                if data.get('l50'):
                    metadata += f"l50: {data['l50']}\n"
                if data.get('busco'):
                    metadata += f"busco: {data['busco']}\n"

                # Software
                if data.get('Acs_name'):
                    metadata += f"Acs_name: {data['Acs_name']}\n"
                if data.get('Software_of_scaffolding'):
                    metadata += f"Software_of_scaffolding: {data['Software_of_scaffolding']}\n"
                if data.get('Software_of_contig_assembly'):
                    metadata += f"Software_of_contig_assembly: {data['Software_of_contig_assembly']}\n"
                if data.get('Software_of_polishing'):
                    metadata += f"Software_of_polishing: {data['Software_of_polishing']}\n"
                if data.get('Software_of_HiC_scaffolding'):
                    metadata += f"Software_of_HiC_scaffolding: {data['Software_of_HiC_scaffolding']}\n"

                # Sizes
                if data.get('Assembled_genome_size_MB'):
                    metadata += f"Assembled_genome_size_MB: {data['Assembled_genome_size_MB']}\n"
                if data.get('Estimated_genome_size_MB'):
                    metadata += f"Estimated_genome_size_MB: {data['Estimated_genome_size_MB']}\n"
                if data.get('Contig_N50_size_KB'):
                    metadata += f"Contig_N50_size_KB: {data['Contig_N50_size_KB']}\n"
                if data.get('Scaffold_N50_size_KB'):
                    metadata += f"Scaffold_N50_size_KB: {data['Scaffold_N50_size_KB']}\n"

                # Platform
                if data.get('Sequencing_platform'):
                    metadata += f"Sequencing_platform: {data['Sequencing_platform']}\n"
                if data.get('Platform_classification'):
                    metadata += f"Platform_classification: {data['Platform_classification']}\n"
                if data.get('Country_or_Institution'):
                    metadata += f"Country_or_Institution: {data['Country_or_Institution']}\n"
                if data.get('If_use_HiC'):
                    metadata += f"If_use_HiC: {data['If_use_HiC']}\n"

                # Publication
                if data.get('Publication'):
                    metadata += f"Publication: {data['Publication']}\n"
                if data.get('Publish_year'):
                    metadata += f"Publish_year: {data['Publish_year']}\n"
                if data.get('PMID_or_DOI'):
                    metadata += f"PMID_or_DOI: {data['PMID_or_DOI']}\n"

            # Add files
            metadata += "files:\n"
            for f in files:
                metadata += f"  - {f}\n"

            with open(metadata_path, 'w') as f:
                f.write(metadata)
            updated += 1

    print(f"Updated {updated} metadata.yaml files")

def main():
    parser = argparse.ArgumentParser(description='Crawl PGCP data')
    parser.add_argument('--output', default='/tmp/pgcp_complete_info.json', help='Output JSON file')
    parser.add_argument('--base-dir', default='/DATA/data2/genomes', help='Base directory for metadata.yaml')
    args = parser.parse_args()

    # Crawl data
    full_data = crawl_pgcp_data()

    # Save to file
    with open(args.output, 'w') as f:
        json.dump(full_data, f, indent=2)
    print(f"Saved to {args.output}")

    # Update metadata.yaml
    update_metadata_yaml(args.base_dir, full_data)

if __name__ == '__main__':
    main()