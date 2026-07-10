#!/usr/bin/env python3
"""Build a queryable PlantGeneWiki graph index from normalized PGCP JSONL outputs."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

DEFAULT_PROCESSED_ROOT = Path("/DATA/data2/plantgenewiki/processed/pgcp_v1")
DEFAULT_OUTPUT_ROOT = Path("/DATA/data2/plantgenewiki/graph/pgcp_v1")

NODE_FILES = (
    "species.jsonl",
    "datasets.jsonl",
    "genes.jsonl",
    "sequence_records.jsonl",
    "gene_locations.jsonl",
    "gene_structures.jsonl",
    "evidence_claims.jsonl",
)


def iter_species_dirs(processed_root: Path) -> Iterable[Path]:
    for path in sorted(processed_root.iterdir(), key=lambda item: item.name):
        if path.is_dir() and (path / "manifest.json").exists():
            yield path


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def record_node_id(record: dict[str, Any], object_type: str | None = None) -> str:
    resolved_type = object_type or str(record.get("object_type") or "Object")
    object_id = str(record.get("object_id") or record.get("id"))
    if resolved_type in {"GeneLocation", "GeneStructure"}:
        return f"{resolved_type}:{object_id}"
    return object_id


def record_label(record: dict[str, Any]) -> str:
    return str(record.get("name") or record.get("id") or record.get("object_id") or "")


def record_species_id(record: dict[str, Any], fallback_species_id: str) -> str:
    value = record.get("species") or record.get("species_id") or fallback_species_id
    if isinstance(value, list):
        value = value[0] if value else fallback_species_id
    value = str(value)
    return value[len("species:"):] if value.startswith("species:") else value


def object_type_from_file(filename: str, record: dict[str, Any]) -> str:
    if filename == "gene_locations.jsonl":
        return "GeneLocation"
    if filename == "gene_structures.jsonl":
        return "GeneStructure"
    return str(record.get("object_type") or "Object")


def node_rows(species_dir: Path, species_id: str) -> Iterable[tuple]:
    for filename in NODE_FILES:
        for record in read_jsonl(species_dir / filename):
            object_type = object_type_from_file(filename, record)
            node_id = record_node_id(record, object_type)
            yield (
                node_id,
                object_type,
                record_label(record),
                record_species_id(record, species_id),
                str(species_dir / filename),
                json.dumps(record, ensure_ascii=False, sort_keys=True),
            )


def relation_row(
    *,
    source: str,
    predicate: str,
    target: str,
    species_id: str,
    source_dataset: str = "",
    evidence: str = "",
    record: dict[str, Any],
) -> tuple:
    return (
        source,
        predicate,
        target,
        species_id,
        source_dataset,
        evidence,
        json.dumps(record, ensure_ascii=False, sort_keys=True),
    )


def edge_rows(species_dir: Path, species_id: str) -> Iterable[tuple]:
    for record in read_jsonl(species_dir / "relations.jsonl"):
        source = str(record.get("source") or "")
        target = str(record.get("target") or "")
        predicate = str(record.get("predicate") or "")
        if not source or not target or not predicate:
            continue
        yield relation_row(
            source=source,
            predicate=predicate,
            target=target,
            species_id=species_id,
            source_dataset=str(record.get("source_dataset") or ""),
            evidence=str(record.get("evidence") or ""),
            record=record,
        )

    for filename, predicate, target_type in (
        ("gene_locations.jsonl", "has_location", "GeneLocation"),
        ("gene_structures.jsonl", "has_structure", "GeneStructure"),
    ):
        for record in read_jsonl(species_dir / filename):
            gene_id = str(record.get("object_id") or record.get("id") or "")
            if not gene_id:
                continue
            target = record_node_id(record, target_type)
            synthetic_record = {
                "source": gene_id,
                "predicate": predicate,
                "target": target,
                "species_id": species_id,
                "source_dataset": record.get("source_dataset") or "",
                "evidence": "derived_from_normalized_record",
            }
            yield relation_row(
                source=gene_id,
                predicate=predicate,
                target=target,
                species_id=species_id,
                source_dataset=str(record.get("source_dataset") or ""),
                evidence="derived_from_normalized_record",
                record=synthetic_record,
            )


def open_database(path: Path, overwrite: bool) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    if overwrite and path.exists():
        path.unlink()
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute("PRAGMA temp_store=MEMORY")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS nodes (
            node_id TEXT PRIMARY KEY,
            object_type TEXT NOT NULL,
            label TEXT,
            species_id TEXT,
            source_file TEXT,
            properties_json TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS edges (
            edge_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            predicate TEXT NOT NULL,
            target TEXT NOT NULL,
            species_id TEXT,
            source_dataset TEXT,
            evidence TEXT,
            properties_json TEXT NOT NULL
        )
        """
    )
    return connection


def create_indexes(connection: sqlite3.Connection) -> None:
    connection.execute("CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(object_type)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_nodes_species ON nodes(species_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_edges_predicate ON edges(predicate)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_edges_species ON edges(species_id)")
    connection.commit()


def build_graph_index(
    *,
    processed_root: Path,
    output_root: Path,
    limit: int | None,
    overwrite: bool,
    batch_size: int,
) -> dict[str, Any]:
    database_path = output_root / "plantgenewiki_pgcp_v1.sqlite"
    connection = open_database(database_path, overwrite=overwrite)
    species_dirs = list(iter_species_dirs(processed_root))
    if limit is not None:
        species_dirs = species_dirs[:limit]

    summary: dict[str, Any] = {
        "processed_root": str(processed_root),
        "output_root": str(output_root),
        "database": str(database_path),
        "species_dirs": len(species_dirs),
        "node_count": 0,
        "edge_count": 0,
        "node_types": Counter(),
        "edge_predicates": Counter(),
        "started_at": datetime.now().isoformat(timespec="seconds"),
    }

    node_buffer: list[tuple] = []
    edge_buffer: list[tuple] = []

    def flush_nodes() -> None:
        if node_buffer:
            connection.executemany(
                """
                INSERT OR REPLACE INTO nodes
                (node_id, object_type, label, species_id, source_file, properties_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                node_buffer,
            )
            node_buffer.clear()

    def flush_edges() -> None:
        if edge_buffer:
            connection.executemany(
                """
                INSERT INTO edges
                (source, predicate, target, species_id, source_dataset, evidence, properties_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                edge_buffer,
            )
            edge_buffer.clear()

    for index, species_dir in enumerate(species_dirs, start=1):
        species_id = species_dir.name
        species_node_count = 0
        species_edge_count = 0
        for row in node_rows(species_dir, species_id):
            node_buffer.append(row)
            summary["node_types"][row[1]] += 1
            summary["node_count"] += 1
            species_node_count += 1
            if len(node_buffer) >= batch_size:
                flush_nodes()
        for row in edge_rows(species_dir, species_id):
            edge_buffer.append(row)
            summary["edge_predicates"][row[1]] += 1
            summary["edge_count"] += 1
            species_edge_count += 1
            if len(edge_buffer) >= batch_size:
                flush_edges()
        connection.commit()
        print(
            json.dumps(
                {
                    "index": index,
                    "species_id": species_id,
                    "nodes": species_node_count,
                    "edges": species_edge_count,
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

    flush_nodes()
    flush_edges()
    connection.commit()
    create_indexes(connection)
    summary["finished_at"] = datetime.now().isoformat(timespec="seconds")
    summary["node_types"] = dict(summary["node_types"])
    summary["edge_predicates"] = dict(summary["edge_predicates"])
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "graph_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    connection.close()
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-root", type=Path, default=DEFAULT_PROCESSED_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=10000)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    summary = build_graph_index(
        processed_root=args.processed_root,
        output_root=args.output_root,
        limit=args.limit,
        overwrite=args.overwrite,
        batch_size=args.batch_size,
    )
    print(json.dumps({"summary": summary}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
