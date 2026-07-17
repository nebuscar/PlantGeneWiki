"""Profile normalized gene records for golden-manifest selection."""

from __future__ import annotations

########## 0. imports ##########
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


########## 1. public api ##########
def profile_gene_candidates(
    species_dir: str | Path,
    limit: int = 5,
) -> dict[str, list[dict[str, Any]]]:
    path = Path(species_dir)
    structures = {
        str(record.get("object_id") or ""): record
        for record in _read_jsonl(path / "gene_structures.jsonl")
    }
    sequences_by_gene: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in _read_jsonl(path / "sequence_records.jsonl"):
        sequences_by_gene[_base_gene_key(str(record.get("inferred_gene_id") or ""))].append(record)

    records = [
        _profile_record(gene, structures, sequences_by_gene)
        for gene in _read_jsonl(path / "genes.jsonl")
    ]
    rankings = {
        "highest_transcript_count": lambda item: item["transcript_count"],
        "highest_sequence_count": lambda item: item["sequence_count"],
        "highest_go_count": lambda item: item["go_count"],
        "highest_cds_feature_count": lambda item: item["cds_feature_count"],
        "longest_description": lambda item: item["description_length"],
    }
    result = {
        name: sorted(records, key=lambda item: (-key(item), item["object_id"]))[:limit]
        for name, key in rankings.items()
    }
    result["transcription_factors"] = [
        item for item in sorted(records, key=lambda item: item["object_id"])
        if item["tf_type"] or item["tf_family"]
    ][:limit]
    result["sparse_annotations"] = [
        item for item in sorted(
            records,
            key=lambda item: (item["go_count"], item["sequence_count"], item["object_id"]),
        )
        if not item["go_count"] and not item["tf_type"] and not item["tf_family"]
    ][:limit]
    return result


########## 2. profiling ##########
def _profile_record(
    gene: dict[str, Any],
    structures: dict[str, dict[str, Any]],
    sequences_by_gene: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    object_id = str(gene.get("object_id") or "")
    structure = structures.get(object_id) or {}
    transcripts = structure.get("transcripts") or []
    annotations = gene.get("annotations") or {}
    transcription_factor = annotations.get("transcription_factor") or {}
    description = str(gene.get("description") or "")
    sequences = sequences_by_gene[_base_gene_key(str(gene.get("id") or object_id))]
    return {
        "object_id": object_id,
        "id": gene.get("id"),
        "name": gene.get("name"),
        "aliases": gene.get("aliases") or [],
        "description": description,
        "strand": (gene.get("genome_location") or {}).get("strand"),
        "go_count": len(annotations.get("go") or []),
        "transcript_count": len(transcripts),
        "sequence_count": len(sequences),
        "cds_feature_count": sum(len(transcript.get("cds") or []) for transcript in transcripts),
        "description_length": len(description),
        "tf_type": transcription_factor.get("type"),
        "tf_family": transcription_factor.get("family"),
    }


########## 3. readers ##########
def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                record = json.loads(line)
                if isinstance(record, dict):
                    yield record


def _base_gene_key(value: str) -> str:
    gene_id = value.rsplit(":", maxsplit=1)[-1]
    return gene_id.split(".", maxsplit=1)[0]
