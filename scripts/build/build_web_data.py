#!/usr/bin/env python3
"""Build static web API data from normalized PlantGeneWiki JSONL records."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = REPO_ROOT / "examples" / "knowledge_objects"
DEFAULT_OUTPUT = REPO_ROOT / "apps" / "web" / "public" / "data" / "api"


class BuildError(RuntimeError):
    pass


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise BuildError(f"Invalid JSON in {path}:{line_number}: {exc}") from exc
        if not isinstance(record, dict):
            raise BuildError(f"Expected object record in {path}:{line_number}")
        records.append(record)
    return records


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require_fields(records: Iterable[dict[str, Any]], fields: list[str], label: str) -> None:
    for record in records:
        missing = [field for field in fields if not record.get(field)]
        if missing:
            identifier = record.get("object_id") or record.get("id") or record
            raise BuildError(f"{label} record {identifier!r} missing fields: {', '.join(missing)}")



def public_dataset_record(record: dict[str, Any]) -> dict[str, Any]:
    public_record = dict(record)
    if public_record.get("location_policy") == "internal_raw_storage":
        public_record["location"] = {
            "type": "internal",
            "label": "internal_raw_storage",
        }
    return public_record

def build_search_index(objects: list[dict[str, Any]], datasets: list[dict[str, Any]]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for record in objects + datasets:
        object_type = record.get("object_type", "Object")
        record_id = str(record["id"])
        if object_type == "Species":
            href = f"/species/{record_id}"
        elif object_type == "Gene":
            href = f"/genes/{record_id}"
        elif object_type == "Dataset":
            href = f"/datasets/{record_id}"
        else:
            href = f"/search#{record_id}"
        items.append(
            {
                "type": str(object_type),
                "id": record_id,
                "title": str(record.get("name", record_id)),
                "href": href,
                "summary": str(record.get("description", "")),
            }
        )
    return sorted(items, key=lambda item: (item["type"], item["title"]))


def build_graph_nodes(objects: list[dict[str, Any]], datasets: list[dict[str, Any]]) -> list[dict[str, str]]:
    nodes = []
    for record in objects + datasets:
        nodes.append(
            {
                "id": str(record["object_id"]),
                "label": str(record.get("name", record["id"])),
                "type": str(record.get("object_type", "Object")),
            }
        )
    return nodes


def build(input_dir: Path, output_dir: Path, clean: bool = True) -> dict[str, int]:
    species = read_jsonl(input_dir / "species.jsonl")
    genes = read_jsonl(input_dir / "genes.jsonl")
    datasets = read_jsonl(input_dir / "datasets.jsonl")
    relations = read_jsonl(input_dir / "relations.jsonl")
    evidence = read_jsonl(input_dir / "evidence_claims.jsonl")

    require_fields(species, ["object_id", "object_type", "id", "name", "description"], "species")
    require_fields(genes, ["object_id", "object_type", "id", "name", "species", "description"], "gene")
    require_fields(datasets, ["object_id", "object_type", "id", "name", "dataset_type", "source", "status"], "dataset")
    require_fields(relations, ["source", "predicate", "target"], "relation")
    require_fields(evidence, ["evidence_id", "source", "claim", "confidence"], "evidence")

    if clean and output_dir.exists():
        shutil.rmtree(output_dir)

    for record in species:
        write_json(output_dir / "species" / f"{record['id']}.json", record)
    for record in genes:
        write_json(output_dir / "genes" / f"{record['id']}.json", record)
    public_datasets = [public_dataset_record(record) for record in datasets]

    for record in public_datasets:
        write_json(output_dir / "datasets" / f"{record['id']}.json", record)

    object_records = species + genes
    write_json(output_dir / "search" / "index.json", build_search_index(object_records, public_datasets))
    write_json(output_dir / "graph" / "nodes.json", build_graph_nodes(object_records, public_datasets))
    write_json(output_dir / "graph" / "edges.json", relations)
    write_json(output_dir / "evidence" / "claims.json", evidence)

    return {
        "species": len(species),
        "genes": len(genes),
        "datasets": len(datasets),
        "relations": len(relations),
        "evidence_claims": len(evidence),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-clean", action="store_true", help="Do not remove existing output directory before writing")
    args = parser.parse_args()

    counts = build(args.input_dir, args.output_dir, clean=not args.no_clean)
    for key, value in counts.items():
        print(f"{key}: {value}")
    print(f"output: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
