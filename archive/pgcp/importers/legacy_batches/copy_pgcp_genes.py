#!/usr/bin/env python3
"""
把爬取的PGCP基因数据复制到/DATA/data2/genomes对应物种文件夹
"""

import os
import shutil

SOURCE_DIR = "/home/nizhu/Projects/PlantGeneWiki/data/pgcp_genes"
TARGET_BASE = "/DATA/data2/genomes"


def find_target_dir(species_underscore):
    """直接扫描目标目录，找最接近的匹配"""
    target_dirs = sorted(os.listdir(TARGET_BASE))

    # 预处理：下划线转空格
    src_lower = species_underscore.replace('_', ' ').lower()

    for td in target_dirs:
        td_lower = td.lower()

        # 方式1: 完全匹配（忽略大小写）
        if src_lower == td_lower:
            return os.path.join(TARGET_BASE, td, "PGCP", "v1")

        # 方式2: 空格-连字符互换后匹配
        if src_lower.replace(' ', '-') == td_lower.replace(' ', '-'):
            return os.path.join(TARGET_BASE, td, "PGCP", "v1")

        # 方式3: 逐词匹配
        src_words = src_lower.split()
        td_words = td_lower.split()
        if len(src_words) == len(td_words):
            all_match = all(sw == tw for sw, tw in zip(src_words, td_words))
            if all_match:
                return os.path.join(TARGET_BASE, td, "PGCP", "v1")

    return None


def main():
    # 获取所有已爬取的物种
    species_list = [d for d in os.listdir(SOURCE_DIR)
                    if os.path.isdir(os.path.join(SOURCE_DIR, d)) and d != 'failed_species.json']

    copied = 0
    skipped = 0
    errors = []

    for species in species_list:
        source_dir = os.path.join(SOURCE_DIR, species)

        # 查找目标目录
        target_dir = find_target_dir(species)

        if target_dir is None:
            errors.append(f"{species}: 目标目录不存在")
            skipped += 1
            continue

        # 复制 genes.json 和 genes.tsv
        for filename in ["genes.json", "genes.tsv"]:
            source_file = os.path.join(source_dir, filename)
            target_file = os.path.join(target_dir, filename)

            if os.path.exists(source_file):
                shutil.copy2(source_file, target_file)

        copied += 1
        print(f"Copied {species} -> {target_dir.split('/')[-4]}")

    print(f"\n{'='*50}")
    print(f"Copied: {copied}")
    print(f"Skipped: {skipped}")
    if errors:
        print(f"Errors: {len(errors)}")
        for e in errors[:10]:
            print(f"  - {e}")


if __name__ == '__main__':
    main()