#!/usr/bin/env python3
"""
从PGCP API批量爬取物种基因数据
"""

import urllib.request
import json
import time
import os
from datetime import datetime

BASE_URL = "https://biobigdata.nju.edu.cn/pgdatabaseAPI/genome"
OUTPUT_DIR = "/home/nizhu/Projects/PlantGeneWiki/data/pgcp_genes"


def get_species_list():
    """获取PGCP所有物种列表"""
    url = "https://biobigdata.nju.edu.cn/pgdatabaseAPI/navlist"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read())
    return data.get('genome', [])


def crawl_species_genes(species_name):
    """爬取单个物种的完整基因数据"""
    url = f"{BASE_URL}?species={species_name}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    resp = urllib.request.urlopen(req, timeout=60)
    data = json.loads(resp.read())
    return data


def save_gene_data(species_name, data):
    """保存基因数据到文件"""
    species_dir = os.path.join(OUTPUT_DIR, species_name)
    os.makedirs(species_dir, exist_ok=True)

    # 保存完整JSON
    output_path = os.path.join(species_dir, "genes.json")
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    # 提取基因列表并保存为TSV
    genes = data.get('species', {}).get('gene', [])
    if genes:
        tsv_path = os.path.join(species_dir, "genes.tsv")
        with open(tsv_path, 'w') as f:
            # 表头
            f.write("gene_ID\tsource_ID\tlocation\tstart\tend\tstrand\tfunction\tgo\ttf_type\ttf_family\n")
            for gene in genes:
                fields = [
                    gene.get('gene_ID', ''),
                    gene.get('source_ID', ''),
                    gene.get('location', ''),
                    str(gene.get('start', '')),
                    str(gene.get('end', '')),
                    gene.get('strand', ''),
                    gene.get('function', '').replace('\t', ' ').replace('\n', ' '),
                    gene.get('go', ''),
                    gene.get('tf_type', ''),
                    gene.get('tf_family', '')
                ]
                f.write('\t'.join(fields) + '\n')

    return len(genes)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 获取物种列表
    print("Fetching species list...")
    species_list = get_species_list()
    print(f"Total species: {len(species_list)}")

    # 统计
    success = 0
    failed = []
    total_genes = 0

    for i, species in enumerate(species_list):
        try:
            print(f"[{i+1}/{len(species_list)}] Crawling {species}...", end=" ")
            data = crawl_species_genes(species)
            gene_count = save_gene_data(species, data)
            success += 1
            total_genes += gene_count
            print(f"OK ({gene_count} genes)")

        except Exception as e:
            print(f"FAILED: {e}")
            failed.append((species, str(e)))

        time.sleep(0.3)  # 避免请求过快

    # 汇总
    print(f"\n{'='*50}")
    print(f"Completed: {success}/{len(species_list)}")
    print(f"Total genes: {total_genes}")
    print(f"Failed: {len(failed)}")
    if failed:
        print("Failed species:")
        for sp, err in failed[:10]:
            print(f"  - {sp}: {err}")

    # 保存失败列表
    if failed:
        with open(os.path.join(OUTPUT_DIR, "failed_species.json"), 'w') as f:
            json.dump(failed, f, indent=2)


if __name__ == '__main__':
    main()