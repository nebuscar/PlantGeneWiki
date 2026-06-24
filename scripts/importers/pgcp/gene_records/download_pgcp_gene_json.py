#!/usr/bin/env python3
"""Download raw PGCP gene JSON files with resumable, bounded concurrency."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


GENOME_API = "https://biobigdata.nju.edu.cn/pgdatabaseAPI/genome"
GENE_API = "https://biobigdata.nju.edu.cn/pgdatabaseAPI/gene"
DEFAULT_API_KEY = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download every raw gene JSON for one PGCP species."
    )
    parser.add_argument("species", help="PGCP species name, e.g. arabidopsis_thaliana")
    parser.add_argument(
        "-o",
        "--output-dir",
        default="data/pgcp_ortho/raw_json",
        help="Directory that will contain raw/*.json and failures.tsv",
    )
    parser.add_argument(
        "--api-key", default=os.environ.get("PGCP_API_KEY", DEFAULT_API_KEY)
    )
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--max-genes", type=int)
    parser.add_argument("--expected-count", type=int)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value)


def request_headers(species: str, gene: str | None, api_key: str) -> dict[str, str]:
    referer = f"https://biobigdata.nju.edu.cn/pgdatabase/genome/{species}"
    if gene:
        referer += f"/details?gene={gene}"
    return {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 PGCP-raw-json-downloader/1.0",
        "X-API-Key": api_key,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": referer,
    }


def request_json(
    url: str, headers: dict[str, str], timeout: float, retries: int
) -> Any:
    for attempt in range(retries + 1):
        try:
            with urlopen(Request(url, headers=headers), timeout=timeout) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt >= retries:
                raise RuntimeError(f"request failed after {retries + 1} attempts: {exc}") from exc
            pause = min(2**attempt, 30)
            print(f"request failed; retrying in {pause}s: {exc}", file=sys.stderr)
            time.sleep(pause)
    raise AssertionError("unreachable")


def extract_gene_ids(payload: Any) -> list[str]:
    species_data = payload.get("species") if isinstance(payload, dict) else None
    genes = species_data.get("gene") if isinstance(species_data, dict) else None
    if not isinstance(genes, list):
        raise ValueError("PGCP genome response does not contain a gene list")

    gene_ids: list[str] = []
    seen: set[str] = set()
    for row in genes:
        gene_id = row.get("gene_ID") if isinstance(row, dict) else None
        if isinstance(gene_id, str) and gene_id and gene_id not in seen:
            seen.add(gene_id)
            gene_ids.append(gene_id)
    return gene_ids


def fetch_gene_ids(
    species: str, api_key: str, timeout: float, retries: int
) -> list[str]:
    url = f"{GENOME_API}?{urlencode({'species': species})}"
    payload = request_json(url, request_headers(species, None, api_key), timeout, retries)
    return extract_gene_ids(payload)


def is_complete_json_file(path: Path) -> bool:
    try:
        size = path.stat().st_size
        if size < 2:
            return False
        with path.open("rb") as handle:
            start = handle.read(min(size, 256)).lstrip()
            handle.seek(max(0, size - 256))
            end = handle.read().rstrip()
        return start.startswith(b"{") and end.endswith(b"}")
    except OSError:
        return False


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    part_path = path.with_suffix(path.suffix + ".part")
    with part_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")
    os.replace(part_path, path)


def fetch_gene_json(
    species: str, gene: str, api_key: str, timeout: float, retries: int
) -> Any:
    url = f"{GENE_API}?{urlencode({'species': species, 'gene': gene})}"
    return request_json(url, request_headers(species, gene, api_key), timeout, retries)


def download_one(
    species: str,
    gene: str,
    raw_dir: Path,
    api_key: str,
    timeout: float,
    retries: int,
    delay: float,
    overwrite: bool,
) -> tuple[str, int]:
    path = raw_dir / f"{safe_name(gene)}.json"
    if not overwrite and is_complete_json_file(path):
        return "cached", path.stat().st_size

    payload = fetch_gene_json(species, gene, api_key, timeout, retries)
    write_json_atomic(path, payload)
    if delay:
        time.sleep(delay)
    return "downloaded", path.stat().st_size


def validate_args(args: argparse.Namespace) -> None:
    if not args.api_key:
        raise ValueError("missing API key")
    if not 1 <= args.workers <= 4:
        raise ValueError("--workers must be between 1 and 4")
    if args.delay < 0 or args.retries < 0 or args.timeout <= 0:
        raise ValueError("--delay/--retries must be non-negative and --timeout positive")
    if args.max_genes is not None and args.max_genes < 1:
        raise ValueError("--max-genes must be positive")


def main() -> int:
    args = parse_args()
    try:
        validate_args(args)
        gene_ids = fetch_gene_ids(args.species, args.api_key, args.timeout, args.retries)
    except (ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.expected_count is not None and len(gene_ids) != args.expected_count:
        print(
            f"error: expected {args.expected_count} genes, PGCP returned {len(gene_ids)}",
            file=sys.stderr,
        )
        return 2
    if args.max_genes is not None:
        gene_ids = gene_ids[: args.max_genes]

    output_dir = Path(args.output_dir)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    failures_path = output_dir / "failures.tsv"
    failure_lock = threading.Lock()
    if not failures_path.exists():
        failures_path.write_text("species\tgene\terror\n", encoding="utf-8")

    print(f"species={args.species} genes={len(gene_ids)} workers={args.workers}", flush=True)
    completed = cached = downloaded = failed = total_bytes = 0
    gene_iter = iter(gene_ids)

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        pending: dict[Any, str] = {}

        def submit_next() -> bool:
            try:
                gene = next(gene_iter)
            except StopIteration:
                return False
            future = executor.submit(
                download_one,
                args.species,
                gene,
                raw_dir,
                args.api_key,
                args.timeout,
                args.retries,
                args.delay,
                args.overwrite,
            )
            pending[future] = gene
            return True

        for _ in range(args.workers):
            submit_next()

        while pending:
            done, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                gene = pending.pop(future)
                completed += 1
                try:
                    status, size = future.result()
                    total_bytes += size
                    if status == "cached":
                        cached += 1
                    else:
                        downloaded += 1
                    print(
                        f"[{completed}/{len(gene_ids)}] {gene} {status} {size} bytes",
                        flush=True,
                    )
                except Exception as exc:
                    failed += 1
                    with failure_lock:
                        with failures_path.open("a", encoding="utf-8") as handle:
                            message = str(exc).replace("\t", " ").replace("\n", " ")
                            handle.write(f"{args.species}\t{gene}\t{message}\n")
                    print(f"[{completed}/{len(gene_ids)}] {gene} FAILED: {exc}", file=sys.stderr, flush=True)
                submit_next()

    print(
        f"finished total={len(gene_ids)} downloaded={downloaded} cached={cached} "
        f"failed={failed} bytes={total_bytes}",
        flush=True,
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
