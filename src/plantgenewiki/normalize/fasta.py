"""Normalize FASTA/FASTA.GZ datasets into PlantGeneWiki knowledge objects."""

from __future__ import annotations

import gzip
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class FastaRecord:
    sequence_id: str
    description: str
    sequence: str


@dataclass(frozen=True)
class NormalizedFastaResult:
    datasets: list[dict]
    sequence_records: list[dict]
    relations: list[dict]
    summary: dict


def open_fasta_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def iter_fasta_records(path: Path) -> Iterator[FastaRecord]:
    current_header: str | None = None
    sequence_parts: list[str] = []

    with open_fasta_text(path) as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if current_header is not None:
                    yield _record_from_header(current_header, sequence_parts)
                current_header = line[1:].strip()
                sequence_parts = []
            else:
                sequence_parts.append(line)

    if current_header is not None:
        yield _record_from_header(current_header, sequence_parts)


def _record_from_header(header: str, sequence_parts: list[str]) -> FastaRecord:
    fields = header.split(maxsplit=1)
    sequence_id = fields[0]
    description = fields[1] if len(fields) > 1 else ""
    sequence = "".join(sequence_parts).upper()
    return FastaRecord(sequence_id=sequence_id, description=description, sequence=sequence)


def normalize_fasta_dataset(
    *,
    input_path: str | Path,
    species_name: str,
    species_id: str,
    source: str,
    version: str,
    sequence_type: str,
    updated_at: str | None = None,
) -> NormalizedFastaResult:
    path = Path(input_path)
    updated_at = updated_at or date.today().isoformat()
    source_id = _slug(source)
    sequence_type_id = _slug(sequence_type)
    dataset_id = f"dataset:{source_id}:{species_id}:{version}:{sequence_type_id}"
    species_object_id = f"species:{species_id}"

    sequence_records: list[dict] = []
    relations: list[dict] = []
    lengths: list[int] = []

    for record in iter_fasta_records(path):
        length = len(record.sequence)
        lengths.append(length)
        sequence_object_id = f"seq:{source_id}:{species_id}:{version}:{sequence_type_id}:{record.sequence_id}"
        inferred_gene_id = infer_gene_id(record.sequence_id)
        sequence_records.append(
            {
                "object_type": "SequenceRecord",
                "object_id": sequence_object_id,
                "id": record.sequence_id,
                "name": record.sequence_id,
                "description": record.description or f"{sequence_type.upper()} sequence record from {source} {version}.",
                "sequence_id": record.sequence_id,
                "species": species_object_id,
                "dataset": dataset_id,
                "sequence_type": sequence_type.upper(),
                "length": length,
                "checksum": {"md5": hashlib.md5(record.sequence.encode("ascii")).hexdigest()},
                "inferred_gene_id": inferred_gene_id,
                "inference_method": "header_parse",
                "confidence": "medium" if inferred_gene_id != record.sequence_id else "low",
                "related_objects": [
                    {"predicate": "contained_in_dataset", "target": dataset_id},
                    {
                        "predicate": "possible_sequence_of",
                        "target": f"gene:{species_id}:{inferred_gene_id}",
                        "confidence": "medium" if inferred_gene_id != record.sequence_id else "low",
                    },
                ],
                "updated_at": updated_at,
            }
        )
        relations.append(
            {
                "source": dataset_id,
                "predicate": "contains_sequence",
                "target": sequence_object_id,
                "evidence": dataset_id,
            }
        )

    summary = build_summary(lengths)
    dataset = {
        "object_type": "Dataset",
        "object_id": dataset_id,
        "id": dataset_id[len("dataset:"):],
        "name": f"{species_name} {source} {version} {sequence_type.upper()} sequences",
        "description": f"{sequence_type.upper()} sequence dataset for {species_name} from {source} {version}.",
        "dataset_type": "sequence_set",
        "species": [species_id],
        "source": source,
        "version": version,
        "sequence_type": sequence_type.upper(),
        "status": "normalized",
        "location_policy": "internal_raw_storage",
        "location": {"type": "local_path", "path": str(path)},
        "file": {
            "format": "fasta.gz" if path.suffix == ".gz" else "fasta",
            "original_filename": path.name,
        },
        "stats": summary,
        "updated_at": updated_at,
    }

    return NormalizedFastaResult(
        datasets=[dataset],
        sequence_records=sequence_records,
        relations=relations,
        summary={**summary, "dataset": dataset_id, "input": str(path)},
    )


def build_summary(lengths: list[int]) -> dict:
    if not lengths:
        return {
            "sequence_count": 0,
            "total_length": 0,
            "min_length": None,
            "max_length": None,
            "mean_length": None,
        }
    total = sum(lengths)
    return {
        "sequence_count": len(lengths),
        "total_length": total,
        "min_length": min(lengths),
        "max_length": max(lengths),
        "mean_length": total / len(lengths),
    }


def infer_gene_id(sequence_id: str) -> str:
    match = re.match(r"^(.+?)\.\d+(?:\.v[0-9][A-Za-z0-9._-]*)?$", sequence_id)
    if match:
        return match.group(1)
    return sequence_id


def write_normalized_fasta_outputs(result: NormalizedFastaResult, output_dir: str | Path) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_path / "datasets.jsonl", result.datasets)
    write_jsonl(output_path / "sequence_records.jsonl", result.sequence_records)
    write_jsonl(output_path / "relations.jsonl", result.relations)
    (output_path / "summary.json").write_text(
        json.dumps(result.summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
