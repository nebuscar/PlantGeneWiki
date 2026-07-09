"""Normalize species-level gene TSV annotations into PlantGeneWiki Gene objects."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class NormalizedGeneTsvResult:
    datasets: list[dict]
    genes: list[dict]
    relations: list[dict]
    evidence_claims: list[dict]
    summary: dict


def normalize_gene_tsv_dataset(
    *,
    input_path: str | Path,
    species_name: str,
    species_id: str,
    source: str,
    version: str,
    import_batch: str,
    assembly: str,
    updated_at: str | None = None,
) -> NormalizedGeneTsvResult:
    path = Path(input_path)
    updated_at = updated_at or date.today().isoformat()
    source_id = _slug(source)
    batch_id = _slug(import_batch)
    dataset_id = f"dataset:{source_id}:{species_id}:{batch_id}:gene_annotation"
    species_object_id = f"species:{species_id}"

    genes: list[dict] = []
    relations: list[dict] = []
    evidence_claims: list[dict] = []

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for index, row in enumerate(reader, start=1):
            gene_id = _clean(row.get("gene_ID"))
            if not gene_id:
                continue
            gene_object_id = f"gene:{species_id}:{gene_id}"
            source_alias = _clean(row.get("source_ID"))
            aliases = [source_alias] if source_alias and source_alias != gene_id else []
            description = _clean(row.get("function")) or f"Gene annotation record for {gene_id}."
            evidence_id = f"evidence:{source_id}:{species_id}:{batch_id}:gene_annotation:{index}"

            gene = {
                "object_type": "Gene",
                "object_id": gene_object_id,
                "id": gene_id,
                "name": gene_id,
                "aliases": aliases,
                "description": description,
                "species": species_id,
                "species_object": species_object_id,
                "source": source,
                "version": version,
                "import_batch": import_batch,
                "datasets": [dataset_id],
                "annotations": _annotations(row),
                "genome_location": _genome_location(row, assembly),
                "related_objects": [
                    {"predicate": "belongs_to_species", "target": species_object_id},
                    {"predicate": "provided_by_dataset", "target": dataset_id},
                ],
                "evidence_records": [evidence_id],
                "updated_at": updated_at,
            }
            genes.append(gene)
            relations.extend(
                [
                    {
                        "source": gene_object_id,
                        "predicate": "belongs_to_species",
                        "target": species_object_id,
                        "evidence": evidence_id,
                        "source_dataset": dataset_id,
                    },
                    {
                        "source": gene_object_id,
                        "predicate": "provided_by_dataset",
                        "target": dataset_id,
                        "evidence": evidence_id,
                        "source_dataset": dataset_id,
                    },
                ]
            )
            evidence_claims.append(
                {
                    "object_type": "EvidenceClaim",
                    "object_id": evidence_id,
                    "id": evidence_id,
                    "evidence_id": evidence_id,
                    "claim_type": "gene_annotation",
                    "subject": gene_object_id,
                    "predicate": "has_annotation",
                    "object": dataset_id,
                    "source": dataset_id,
                    "claim": f"{gene_id} has a gene annotation record in {path.name}.",
                    "evidence_type": "gene_annotation_table",
                    "evidence_text": description,
                    "source_provider": source,
                    "source_dataset": dataset_id,
                    "confidence": "medium",
                    "updated_at": updated_at,
                }
            )

    dataset = {
        "object_type": "Dataset",
        "object_id": dataset_id,
        "id": dataset_id[len("dataset:"):],
        "name": f"{species_name} gene annotation table",
        "description": f"Species-level gene annotation table for {species_name}.",
        "dataset_type": "gene_annotation",
        "species": [species_id],
        "source": source,
        "version": version,
        "import_batch": import_batch,
        "assembly": assembly,
        "status": "normalized",
        "location_policy": "internal_raw_storage",
        "location": {"type": "internal", "label": "internal_raw_storage"},
        "file": {
            "format": "tsv",
            "original_filename": path.name,
        },
        "stats": {"gene_count": len(genes)},
        "updated_at": updated_at,
    }

    return NormalizedGeneTsvResult(
        datasets=[dataset],
        genes=genes,
        relations=relations,
        evidence_claims=evidence_claims,
        summary={"gene_count": len(genes), "dataset": dataset_id, "input_file": path.name},
    )


def _annotations(row: dict[str, str | None]) -> dict:
    annotations: dict = {}
    go_terms = _split_semicolon(row.get("go"))
    if go_terms:
        annotations["go"] = go_terms

    tf_type = _clean(row.get("tf_type"))
    tf_family = _clean(row.get("tf_family"))
    if tf_type or tf_family:
        annotations["transcription_factor"] = {
            "type": tf_type or None,
            "family": tf_family or None,
        }
    return annotations


def _genome_location(row: dict[str, str | None], assembly: str) -> dict | None:
    seqid = _clean(row.get("location"))
    start = _int_or_none(row.get("start"))
    end = _int_or_none(row.get("end"))
    strand = _clean(row.get("strand"))
    if not seqid or start is None or end is None:
        return None
    return {
        "assembly": assembly,
        "seqid": seqid,
        "start": start,
        "end": end,
        "strand": strand or None,
        "coordinate_system": "1-based-closed",
    }


def _split_semicolon(value: str | None) -> list[str]:
    return [item for item in (_clean(part) for part in (value or "").split(";")) if item]


def _int_or_none(value: str | None) -> int | None:
    value = _clean(value)
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
