#!/usr/bin/env python3
"""
PGCP (Plant Genome Comparison Platform) 下载工具
通过 biobigdata API 下载文件

用法:
    python3 download_api.py species --output-dir ./downloads
    python3 download_api.py abies_alba --files "*.genomic.fa.gz"
    python3 download_api.py list  # 列出所有物种
"""

import json
import urllib.request
import urllib.error
import argparse
import os
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "https://biobigdata.nju.edu.cn/pgdatabaseAPI"
DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "meta" / "pgcp"


def load_download_list():
    """加载下载列表数据"""
    json_file = DATA_DIR / "biobigdata_downloads.json"
    if json_file.exists():
        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)
    # 如果JSON不存在，从API获取
    print("正在从API获取数据...")
    url = f"{BASE_URL}/downloadlist"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_file(file_name: str, species: str, output_dir: Path) -> bool:
    """通过API下载单个文件"""
    url = f"{BASE_URL}/download"
    data = json.dumps({"files": [file_name]}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "json" in content_type:
                # API返回了错误信息
                error = json.loads(resp.read().decode("utf-8"))
                print(f"  错误: {error}")
                return False
            # 保存文件
            output_path = output_dir / file_name
            with open(output_path, "wb") as f:
                f.write(resp.read())
            return True
    except urllib.error.URLError as e:
        print(f"  下载失败: {e}")
        return False


def list_species(data):
    """列出所有物种"""
    species = sorted(set(item["species"] for item in data))
    print(f"共 {len(species)} 个物种:\n")
    for i, sp in enumerate(species, 1):
        print(f"{i:4d}. {sp}")
    return species


def download_species_files(species: str, file_pattern: str = None, output_dir: Path = None, max_workers: int = 3):
    """下载指定物种的文件"""
    data = load_download_list()
    output_dir = output_dir or Path(".") / species
    output_dir.mkdir(parents=True, exist_ok=True)

    # 筛选文件
    files = [f for f in data if f["species"] == species]
    if file_pattern:
        import fnmatch
        files = [f for f in files if fnmatch.fnmatch(f["file"], file_pattern)]

    if not files:
        print(f"未找到匹配的文件: {species} ({file_pattern})")
        return

    print(f"找到 {len(files)} 个文件，开始下载到 {output_dir}")
    success, failed = 0, 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(download_file, f["file"], species, output_dir): f["file"]
            for f in files
        }
        for future in as_completed(futures):
            file_name = futures[future]
            if future.result():
                success += 1
                print(f"  [OK] {file_name}")
            else:
                failed += 1
                print(f"  [FAIL] {file_name}")

    print(f"\n完成: 成功 {success}, 失败 {failed}")


def main():
    parser = argparse.ArgumentParser(description="PGCP 数据下载工具")
    subparsers = parser.add_subparsers(dest="cmd")

    # list 命令
    subparsers.add_parser("list", help="列出所有物种")

    # species 命令
    species_parser = subparsers.add_parser("species", help="下载指定物种的文件")
    species_parser.add_argument("species", help="物种名称")
    species_parser.add_argument("--pattern", "-p", default=None, help="文件匹配模式，如 *.genomic.fa.gz")
    species_parser.add_argument("--output", "-o", default=None, help="输出目录")
    species_parser.add_argument("--workers", "-w", type=int, default=3, help="并发下载数")

    args = parser.parse_args()

    data = load_download_list()

    if args.cmd == "list":
        list_species(data)
    elif args.cmd == "species":
        download_species_files(
            args.species,
            file_pattern=args.pattern,
            output_dir=Path(args.output) if args.output else None,
            max_workers=args.workers,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
