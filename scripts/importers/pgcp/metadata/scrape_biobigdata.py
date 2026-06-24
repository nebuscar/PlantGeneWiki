#!/usr/bin/env python3
"""
爬取 biobigdata.nju.edu.cn/pgdatabase 下载数据元信息
整理成数据信息表: File Name, File Type, File Size, Species, Last Modified
"""

import json
import urllib.request
import urllib.error
import time
from pathlib import Path

URL = "https://biobigdata.nju.edu.cn/pgdatabaseAPI/downloadlist"
OUTPUT_DIR = Path("/home/nizhu/Projects/PlantGeneWiki/data/meta/pgcp")
OUTPUT_FILE = OUTPUT_DIR / "biobigdata_downloads.tsv"


def fetch_data():
    """获取API数据，带重试机制"""
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    req = urllib.request.Request(URL, headers=headers)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            print(f"请求失败 (尝试 {attempt + 1}/3): {e}")
            if attempt < 2:
                time.sleep(5)
    raise RuntimeError("无法获取数据")


def format_size(size_bytes: int) -> str:
    """字节转换为人类可读格式"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("正在从 biobigdata 获取数据...")
    data = fetch_data()
    print(f"获取到 {len(data)} 条记录")

    # 提取文件类型后缀
    type_mapping = {}
    for item in data:
        fname = item["file"]
        ftype = item["type"]
        if fname not in type_mapping:
            type_mapping[fname] = ftype

    # 写入TSV (按物种和文件名排序)
    data.sort(key=lambda x: (x["species"], x["file"]))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("File Name\tFile Type\tFile Size\tSize (Bytes)\tSpecies\tLast Modified\n")
        for item in data:
            f.write(
                f"{item['file']}\t"
                f"{item['type']}\t"
                f"{format_size(item['size'])}\t"
                f"{item['size']}\t"
                f"{item['species']}\t"
                f"{item['mtime']}\n"
            )

    print(f"数据已保存至: {OUTPUT_FILE}")

    # 生成汇总统计
    stats_file = OUTPUT_DIR / "biobigdata_stats.txt"
    species_set = set(item["species"] for item in data)
    type_counts = {}
    total_size = 0
    for item in data:
        type_counts[item["type"]] = type_counts.get(item["type"], 0) + 1
        total_size += item["size"]

    with open(stats_file, "w", encoding="utf-8") as f:
        f.write(f"BioBigData 下载数据统计\n")
        f.write(f"{'=' * 50}\n\n")
        f.write(f"总文件数: {len(data)}\n")
        f.write(f"物种数: {len(species_set)}\n")
        f.write(f"总大小: {format_size(total_size)}\n\n")
        f.write(f"文件类型分布:\n")
        for ftype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            f.write(f"  {ftype}: {count}\n")

    print(f"统计已保存至: {stats_file}")


if __name__ == "__main__":
    main()
