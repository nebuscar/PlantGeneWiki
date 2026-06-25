"""Normalize GFF3/GFF3.GZ genome annotations into PlantGeneWiki objects."""

from __future__ import annotations

import gzip
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterator
from urllib.parse import unquote


@dataclass(frozen=True)
class GffFeature:
    seqid: str
    source: str
    feature_type: str
    start: int
    end: int
    score: str
    strand: str
    phase: str
    attributes: dict[str, str]


@dataclass(frozen=True)
class NormalizedGffResult:
    datasets: list[dict]
    gene_locations: list[dict]
    gene_structures: list[dict]
    relations: list[dict]
    manifest: dict
    summary: dict


def open_gff_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def parse_gff_attributes(attr_text: str) -> dict[str, str]:
    attributes: dict[str, str] = {}
    for part in attr_text.strip().strip(";").split(";"):
        if not part:
            continue
        if "=" in part:
            key, value = part.split("=", 1)
        elif " " in part:
            key, value = part.split(" ", 1)
            value = value.strip().strip('"')
        else:
            attributes[part] = ""
            continue
        attributes[unquote(key.strip())] = unquote(value.strip())
    return attributes


def iter_gff_features(path: str | Path) -> Iterator[GffFeature]:
    gff_path = Path(path)
    with open_gff_text(gff_path) as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split("	")
            if len(fields) != 9:
                continue
            seqid, source, feature_type, start, end, score, strand, phase, attrs = fields
            yield GffFeature(
                seqid=seqid,
                source=source,
                feature_type=feature_type,
                start=int(start),
                end=int(end),
                score=score,
                strand=strand,
                phase=phase,
                attributes=parse_gff_attributes(attrs),
            )


def normalize_gff3_dataset(
    *,
    input_path: str | Path,
    species_name: str,
    species_id: str,
    source: str,
    version: str,
    assembly: str,
    updated_at: str | None = None,
) -> NormalizedGffResult:
    path = Path(input_path)
    updated_at = updated_at or date.today().isoformat()
    source_id = _slug(source)
    dataset_id = f"dataset:{source_id}:{species_id}:{version}:genome_annotation"
    species_object_id = f"species:{species_id}"

    genes: dict[str, GffFeature] = {}
    transcripts: dict[str, GffFeature] = {}
    transcript_to_gene: dict[str, str] = {}
    child_features: dict[str, list[GffFeature]] = defaultdict(list)
    feature_counts: Counter[str] = Counter()

    for feature in iter_gff_features(path):
        feature_counts[feature.feature_type] += 1
        feature_id = feature.attributes.get("ID")
        parent_id = _first_parent(feature.attributes.get("Parent"))

        if feature.feature_type == "gene" and feature_id:
            genes[feature_id] = feature
        elif feature.feature_type in {"mRNA", "transcript"} and feature_id:
            transcripts[feature_id] = feature
            if parent_id:
                transcript_to_gene[feature_id] = parent_id
        elif parent_id:
            child_features[parent_id].append(feature)

    gene_locations: list[dict] = []
    gene_structures: list[dict] = []
    relations: list[dict] = []

    for gene_id, gene in genes.items():
        gene_object_id = f"gene:{species_id}:{gene_id}"
        gene_name = gene.attributes.get("Name") or gene_id
        transcript_records = []
        transcript_ids = [tid for tid, parent in transcript_to_gene.items() if parent == gene_id]
        transcript_ids.sort(key=lambda tid: (transcripts[tid].start, transcripts[tid].end, tid))
        primary_transcript = transcript_ids[0] if transcript_ids else None

        for transcript_id in transcript_ids:
            transcript = transcripts[transcript_id]
            features = child_features.get(transcript_id, [])
            transcript_records.append(
                {
                    "transcript_id": transcript_id,
                    "name": transcript.attributes.get("Name") or transcript_id,
                    "location": _location(transcript, assembly),
                    "exons": [_feature_interval(item) for item in _features_of_type(features, {"exon"})],
                    "cds": [_feature_interval(item, include_phase=True) for item in _features_of_type(features, {"CDS"})],
                    "utrs": [_feature_interval(item) for item in _features_of_type(features, {"five_prime_UTR", "three_prime_UTR", "UTR"})],
                    "attributes": _selected_attributes(transcript.attributes),
                }
            )

        gene_locations.append(
            {
                "object_type": "Gene",
                "object_id": gene_object_id,
                "name": gene_name,
                "species": species_object_id,
                "source_dataset": dataset_id,
                "genome_location": _location(gene, assembly),
                "feature_ids": {
                    "gene": gene_id,
                    "primary_transcript": primary_transcript,
                },
                "attributes": _selected_attributes(gene.attributes),
                "updated_at": updated_at,
            }
        )
        gene_structures.append(
            {
                "object_type": "GeneStructure",
                "object_id": gene_object_id,
                "gene_feature_id": gene_id,
                "source_dataset": dataset_id,
                "transcripts": transcript_records,
                "updated_at": updated_at,
            }
        )
        relations.append(
            {
                "source": dataset_id,
                "predicate": "contains_gene",
                "target": gene_object_id,
                "evidence": dataset_id,
            }
        )

    stats = {
        "gene_count": len(gene_locations),
        "transcript_count": len(transcripts),
        "feature_counts": dict(sorted(feature_counts.items())),
    }
    dataset = {
        "object_type": "Dataset",
        "object_id": dataset_id,
        "id": dataset_id[len("dataset:"):],
        "name": f"{species_name} {source} {version} genome annotation",
        "description": f"Genome annotation dataset for {species_name} from {source} {version}.",
        "dataset_type": "genome_annotation",
        "species": [species_id],
        "source": source,
        "version": version,
        "assembly": assembly,
        "status": "normalized",
        "coordinate_system": "1-based-closed",
        "location_policy": "internal_raw_storage",
        "location": {"type": "local_path", "path": str(path)},
        "file": {
            "format": "gff3.gz" if path.suffix == ".gz" else "gff3",
            "original_filename": path.name,
        },
        "stats": stats,
        "updated_at": updated_at,
    }
    manifest = {
        "dataset_id": dataset_id,
        "object_type": "Dataset",
        "dataset_type": "genome_annotation",
        "species": species_object_id,
        "assembly": assembly,
        "source": source,
        "version": version,
        "raw_file": str(path),
        "normalized_files": {
            "datasets": "datasets.jsonl",
            "gene_locations": "gene_locations.jsonl",
            "gene_structures": "gene_structures.jsonl",
            "relations": "relations.jsonl",
            "igv_annotation": None,
            "igv_annotation_index": None,
        },
        "coordinate_system": "1-based-closed",
        "feature_counts": stats["feature_counts"],
        "updated_at": updated_at,
    }

    return NormalizedGffResult(
        datasets=[dataset],
        gene_locations=gene_locations,
        gene_structures=gene_structures,
        relations=relations,
        manifest=manifest,
        summary={**stats, "dataset": dataset_id, "input": str(path)},
    )


def write_normalized_gff_outputs(result: NormalizedGffResult, output_dir: str | Path) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_path / "datasets.jsonl", result.datasets)
    write_jsonl(output_path / "gene_locations.jsonl", result.gene_locations)
    write_jsonl(output_path / "gene_structures.jsonl", result.gene_structures)
    write_jsonl(output_path / "relations.jsonl", result.relations)
    newline = chr(10)
    (output_path / "annotation_manifest.json").write_text(
        json.dumps(result.manifest, ensure_ascii=False, indent=2, sort_keys=True) + newline,
        encoding="utf-8",
    )
    (output_path / "summary.json").write_text(
        json.dumps(result.summary, ensure_ascii=False, indent=2, sort_keys=True) + newline,
        encoding="utf-8",
    )


def write_jsonl(path: Path, records: list[dict]) -> None:
    newline = chr(10)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + newline for record in records),
        encoding="utf-8",
    )


def _location(feature: GffFeature, assembly: str) -> dict:
    return {
        "assembly": assembly,
        "seqid": feature.seqid,
        "start": feature.start,
        "end": feature.end,
        "strand": feature.strand,
        "coordinate_system": "1-based-closed",
    }


def _feature_interval(feature: GffFeature, include_phase: bool = False) -> dict:
    interval = {
        "id": feature.attributes.get("ID"),
        "seqid": feature.seqid,
        "start": feature.start,
        "end": feature.end,
        "strand": feature.strand,
        "feature_type": feature.feature_type,
    }
    if include_phase:
        interval["phase"] = feature.phase
    return interval


def _features_of_type(features: list[GffFeature], feature_types: set[str]) -> list[GffFeature]:
    return sorted(
        [feature for feature in features if feature.feature_type in feature_types],
        key=lambda feature: (feature.start, feature.end, feature.attributes.get("ID", "")),
    )


def _first_parent(parent: str | None) -> str | None:
    if not parent:
        return None
    return parent.split(",", 1)[0]


def _selected_attributes(attributes: dict[str, str]) -> dict[str, str]:
    selected_keys = ["ID", "Name", "Source_ID", "biotype", "gene_biotype", "transcript_biotype"]
    return {key: attributes[key] for key in selected_keys if key in attributes}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
