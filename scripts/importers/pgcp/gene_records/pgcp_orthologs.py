#!/usr/bin/env python3
"""Batch-download PGCP ortholog records, one result table per query species."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import defaultdict
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = "https://biobigdata.nju.edu.cn/pgdatabaseAPI/gene"
DEFAULT_API_KEY = ""
CSV_FIELDS = [
    "query_species",
    "query_gene",
    "source_gene",
    "dataset",
    "Orthogroup",
    "Ortho",
    "Score",
    "Similarity",
    "Species",
    "Trans_gene",
]
INPUT_SUFFIXES = {".txt", ".tsv", ".csv"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="按物种批量获取、保存 PGCP 基因同源记录。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "input",
        help=(
            "基因列表文件、包含多个物种基因列表的目录；"
            "使用 --all-genes 时填写物种名或物种名列表文件。"
            "目录模式下文件名需为物种名，如 arabidopsis_thaliana.txt"
        ),
    )
    parser.add_argument(
        "-s",
        "--species",
        default="arabidopsis_thaliana",
        help="单个输入文件中，单列基因 ID 使用的默认查询物种",
    )
    parser.add_argument(
        "-o", "--output-dir", default="outputs/pgcp_by_species", help="输出目录"
    )
    parser.add_argument(
        "--dataset",
        choices=("ortho", "ortho_whole", "both"),
        default="ortho_whole",
        help="提取返回 JSON 中的哪一部分",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("PGCP_API_KEY", DEFAULT_API_KEY),
        help="PGCP API key，也可通过 PGCP_API_KEY 环境变量设置",
    )
    parser.add_argument("--delay", type=float, default=1.0, help="请求间隔秒数")
    parser.add_argument("--timeout", type=float, default=30.0, help="请求超时秒数")
    parser.add_argument("--retries", type=int, default=3, help="失败后的最大重试次数")
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="并发处理基因数量；建议不超过 3，避免给服务器造成过大压力",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="重新请求已有原始 JSON 的基因，而非断点续跑",
    )
    parser.add_argument(
        "--all-genes",
        action="store_true",
        help="自动获取指定物种的全部基因，再逐个抓取同源记录",
    )
    parser.add_argument(
        "--max-genes",
        type=int,
        default=None,
        help="每个物种最多处理多少个基因，主要用于小批量测试",
    )
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value)


def parse_query_lines(
    lines: Iterable[str], default_species: str, source: str
) -> list[tuple[str, str]]:
    queries: list[tuple[str, str]] = []
    for line_number, line in enumerate(lines, 1):
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        parts = re.split(r"[\t, ]+", text)
        if len(parts) == 1:
            queries.append((default_species, parts[0]))
        elif len(parts) == 2:
            queries.append((parts[0], parts[1]))
        else:
            raise ValueError(f"{source} 第 {line_number} 行格式错误：{text}")
    return queries


def read_query_file(path: Path, default_species: str) -> list[tuple[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return parse_query_lines(handle, default_species, str(path))


def read_queries(path: Path, default_species: str) -> list[tuple[str, str]]:
    queries: list[tuple[str, str]] = []
    if path.is_dir():
        files = sorted(
            item
            for item in path.iterdir()
            if item.is_file() and item.suffix.lower() in INPUT_SUFFIXES
        )
        if not files:
            raise ValueError(f"目录中没有 .txt、.tsv 或 .csv 基因列表：{path}")
        for file_path in files:
            queries.extend(read_query_file(file_path, file_path.stem))
    else:
        queries.extend(read_query_file(path, default_species))

    seen: set[tuple[str, str]] = set()
    unique: list[tuple[str, str]] = []
    for query in queries:
        if query not in seen:
            seen.add(query)
            unique.append(query)
    return unique


def read_species_names(value: str) -> list[str]:
    path = Path(value)
    if path.is_file():
        names = [
            line.strip().split()[0]
            for line in path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    else:
        names = [item.strip() for item in value.split(",") if item.strip()]
    return list(dict.fromkeys(names))


def request_json(url: str, headers: dict[str, str], timeout: float, retries: int) -> Any:
    for attempt in range(retries + 1):
        try:
            with urlopen(Request(url, headers=headers), timeout=timeout) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt >= retries:
                raise RuntimeError(f"请求失败：{exc}") from exc
            wait = min(2**attempt, 10)
            print(f"  请求失败，{wait} 秒后重试：{exc}", file=sys.stderr)
            time.sleep(wait)
    raise AssertionError("unreachable")


def request_headers(species: str, gene: str | None, api_key: str) -> dict[str, str]:
    referer = f"https://biobigdata.nju.edu.cn/pgdatabase/genome/{species}"
    if gene:
        referer += f"/details?gene={gene}"
    return {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 PGCP-ortholog-batch-downloader/3.0",
        "X-API-Key": api_key,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": referer,
    }


def fetch_species_genes(
    species: str, api_key: str, timeout: float, retries: int
) -> list[dict[str, Any]]:
    url = f"https://biobigdata.nju.edu.cn/pgdatabaseAPI/genome?{urlencode({'species': species})}"
    data = request_json(url, request_headers(species, None, api_key), timeout, retries)
    species_data = data.get("species") if isinstance(data, dict) else None
    genes = species_data.get("gene") if isinstance(species_data, dict) else None
    if not isinstance(genes, list):
        raise RuntimeError(f"物种 {species} 的 genome 接口未返回基因列表")
    return [gene for gene in genes if isinstance(gene, dict) and gene.get("gene_ID")]


def write_gene_metadata(path: Path, genes: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for gene in genes for key in gene})
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(genes)


def read_gene_metadata(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle) if row.get("gene_ID")]


def build_all_gene_queries(args: argparse.Namespace, output_dir: Path) -> list[tuple[str, str]]:
    queries: list[tuple[str, str]] = []
    for species in read_species_names(args.input):
        genes_path = (
            output_dir / "by_query_species" / safe_name(species) / "genes.csv"
        )
        if genes_path.exists() and not args.overwrite:
            print(f"使用已有物种基因列表：{species}", flush=True)
            genes = read_gene_metadata(genes_path)
        else:
            print(f"获取物种基因列表：{species}", flush=True)
            genes = fetch_species_genes(species, args.api_key, args.timeout, args.retries)
            write_gene_metadata(genes_path, genes)
        if args.max_genes is not None:
            genes = genes[: args.max_genes]
        queries.extend((species, str(gene["gene_ID"])) for gene in genes)
        print(f"  将处理 {len(genes)} 个基因", flush=True)
    return queries


def fetch_gene(
    species: str, gene: str, api_key: str, timeout: float, retries: int
) -> dict[str, Any]:
    url = f"{API_URL}?{urlencode({'species': species, 'gene': gene})}"
    return request_json(
        url, request_headers(species, gene, api_key), timeout, retries
    )


def selected_datasets(name: str) -> tuple[str, ...]:
    return ("ortho", "ortho_whole") if name == "both" else (name,)


def extract_rows(
    data: dict[str, Any], query_species: str, query_gene: str, dataset: str
) -> tuple[list[dict[str, Any]], list[tuple[str, str, str, str]]]:
    rows: list[dict[str, Any]] = []
    trees: list[tuple[str, str, str, str]] = []
    section = data.get(dataset) or {}
    if not isinstance(section, dict):
        return rows, trees

    for source_gene, groups in section.items():
        if not isinstance(groups, dict):
            continue
        for orthogroup, group_data in groups.items():
            if not isinstance(group_data, dict):
                continue
            for item in group_data.get("table") or []:
                if not isinstance(item, dict):
                    continue
                row = {
                    "query_species": query_species,
                    "query_gene": query_gene,
                    "source_gene": source_gene,
                    "dataset": dataset,
                }
                row.update(item)
                row["Orthogroup"] = row.get("Orthogroup") or orthogroup
                rows.append({field: row.get(field, "") for field in CSV_FIELDS})
            tree = group_data.get("tree")
            if tree:
                trees.append((dataset, source_gene, orthogroup, str(tree)))
    return rows, trees


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_failures(path: Path, failures: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["species", "gene", "error"])
        writer.writeheader()
        writer.writerows(failures)


def write_species_failures(output_dir: Path, failures: list[dict[str, str]]) -> None:
    failures_by_species: dict[str, list[dict[str, str]]] = defaultdict(list)
    for failure in failures:
        failures_by_species[failure["species"]].append(failure)
    for species, species_failures in failures_by_species.items():
        write_failures(
            output_dir / "by_query_species" / safe_name(species) / "failures.csv",
            species_failures,
        )


def process_query(
    species: str,
    gene: str,
    output_dir: Path,
    datasets: tuple[str, ...],
    api_key: str,
    timeout: float,
    retries: int,
    overwrite: bool,
    delay: float,
) -> tuple[list[dict[str, Any]], bool]:
    species_dir = output_dir / "by_query_species" / safe_name(species)
    raw_dir = species_dir / "raw"
    tree_dir = species_dir / "trees"
    raw_dir.mkdir(parents=True, exist_ok=True)
    tree_dir.mkdir(parents=True, exist_ok=True)
    stem = safe_name(gene)
    raw_path = raw_dir / f"{stem}.json"
    cached = raw_path.exists() and not overwrite

    if cached:
        with raw_path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    else:
        data = fetch_gene(species, gene, api_key, timeout, retries)
        with raw_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        if delay:
            time.sleep(delay)

    gene_rows: list[dict[str, Any]] = []
    for dataset in datasets:
        rows, trees = extract_rows(data, species, gene, dataset)
        gene_rows.extend(rows)
        for tree_dataset, source_gene, orthogroup, tree in trees:
            tree_name = safe_name(
                f"{stem}__{tree_dataset}__{source_gene}__{orthogroup}.nwk"
            )
            (tree_dir / tree_name).write_text(tree + "\n", encoding="utf-8")
    return gene_rows, cached


def main() -> int:
    args = parse_args()
    if not args.api_key:
        print("错误：请通过 --api-key 或 PGCP_API_KEY 提供 API key。", file=sys.stderr)
        return 2
    if args.delay < 0 or args.retries < 0:
        print("错误：--delay 和 --retries 不能为负数。", file=sys.stderr)
        return 2
    if args.max_genes is not None and args.max_genes < 1:
        print("错误：--max-genes 必须大于 0。", file=sys.stderr)
        return 2
    if args.workers < 1 or args.workers > 8:
        print("错误：--workers 必须在 1 到 8 之间。", file=sys.stderr)
        return 2

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        queries = (
            build_all_gene_queries(args, output_dir)
            if args.all_genes
            else read_queries(input_path, args.species)
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    if not queries:
        print("错误：输入中没有有效基因或物种。", file=sys.stderr)
        return 2

    failures: list[dict[str, str]] = []
    datasets = selected_datasets(args.dataset)
    query_species = list(dict.fromkeys(species for species, _ in queries))
    total_rows = 0

    with ExitStack() as stack:
        all_handle = stack.enter_context(
            (output_dir / "orthologs_all.csv").open(
                "w", newline="", encoding="utf-8-sig"
            )
        )
        all_writer = csv.DictWriter(all_handle, fieldnames=CSV_FIELDS)
        all_writer.writeheader()
        species_writers: dict[str, csv.DictWriter] = {}
        for species in query_species:
            species_path = (
                output_dir / "by_query_species" / safe_name(species) / "orthologs.csv"
            )
            species_path.parent.mkdir(parents=True, exist_ok=True)
            handle = stack.enter_context(
                species_path.open("w", newline="", encoding="utf-8-sig")
            )
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            writer.writeheader()
            species_writers[species] = writer

        completed = 0
        query_iter = iter(queries)
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            pending = {}

            def submit_next() -> bool:
                try:
                    species, gene = next(query_iter)
                except StopIteration:
                    return False
                future = executor.submit(
                    process_query,
                    species,
                    gene,
                    output_dir,
                    datasets,
                    args.api_key,
                    args.timeout,
                    args.retries,
                    args.overwrite,
                    args.delay,
                )
                pending[future] = (species, gene)
                return True

            for _ in range(args.workers):
                submit_next()

            while pending:
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    species, gene = pending.pop(future)
                    completed += 1
                    try:
                        gene_rows, cached = future.result()
                        all_writer.writerows(gene_rows)
                        species_writers[species].writerows(gene_rows)
                        total_rows += len(gene_rows)
                        cache_note = "，使用缓存" if cached else ""
                        print(
                            f"[{completed}/{len(queries)}] {species} / {gene}："
                            f"{len(gene_rows)} 条{cache_note}",
                            flush=True,
                        )
                    except Exception as exc:
                        failures.append(
                            {"species": species, "gene": gene, "error": str(exc)}
                        )
                        print(
                            f"[{completed}/{len(queries)}] {species} / {gene} "
                            f"失败：{exc}",
                            file=sys.stderr,
                            flush=True,
                        )
                    submit_next()

    write_failures(output_dir / "failures_all.csv", failures)
    write_species_failures(output_dir, failures)

    print(
        f"完成：{len(queries) - len(failures)}/{len(queries)} 个查询成功，"
        f"共 {total_rows} 条记录。"
    )
    print(f"查询物种数：{len(query_species)}")
    print(f"输出目录：{output_dir}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
