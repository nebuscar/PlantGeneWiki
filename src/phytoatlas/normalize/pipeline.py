"""Build a minimal species knowledge graph from normalized genome sources."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from phytoatlas.normalize.fasta import normalize_fasta_dataset, write_jsonl
from phytoatlas.normalize.gene_tsv import normalize_gene_tsv_dataset
from phytoatlas.normalize.gff import normalize_gff3_dataset


def build_minimal_species_knowledge_base(
    *,
    species_name: str,
    species_id: str,
    fasta_paths: Iterable[str | Path],
    gff_path: str | Path | None,
    gene_tsv_path: str | Path,
    output_dir: str | Path,
    source_provider: str,
    import_batch: str,
    version: str,
    assembly: str,
    updated_at: str | None = None,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    gene_tsv_result = normalize_gene_tsv_dataset(
        input_path=gene_tsv_path,
        species_name=species_name,
        species_id=species_id,
        source=source_provider,
        version=version,
        import_batch=import_batch,
        assembly=assembly,
        updated_at=updated_at,
    )

    gff_result = None
    if gff_path is not None:
        gff_result = normalize_gff3_dataset(
            input_path=gff_path,
            species_name=species_name,
            species_id=species_id,
            source=source_provider,
            version=version,
            assembly=assembly,
            updated_at=updated_at,
        )

    fasta_results = [
        normalize_fasta_dataset(
            input_path=fasta_path,
            species_name=species_name,
            species_id=species_id,
            source=source_provider,
            version=version,
            sequence_type=_sequence_type_from_path(Path(fasta_path)),
            updated_at=updated_at,
        )
        for fasta_path in fasta_paths
    ]

    location_by_gene = {}
    if gff_result:
        for location in gff_result.gene_locations:
            gene_identifier = location["object_id"].rsplit(":", 1)[-1]
            location_by_gene[_base_gene_key(gene_identifier)] = location

    sequence_by_gene: dict[str, list[dict[str, Any]]] = {}
    for fasta_result in fasta_results:
        for sequence_record in fasta_result.sequence_records:
            sequence_by_gene.setdefault(
                _base_gene_key(sequence_record.get("inferred_gene_id") or sequence_record["sequence_id"]),
                [],
            ).append(sequence_record)

    genes = []
    relations = list(gene_tsv_result.relations)
    for gene in gene_tsv_result.genes:
        merged = dict(gene)
        base_key = _base_gene_key(gene["id"])
        location = location_by_gene.get(base_key)
        if location:
            merged["name"] = location.get("name") or merged["name"]
            merged["genome_location"] = location.get("genome_location")
            merged["gene_location"] = location["object_id"]
        sequences = sequence_by_gene.get(base_key, [])
        if sequences:
            merged["sequence_records"] = [sequence["object_id"] for sequence in sequences]
            existing_relations = list(merged.get("related_objects", []))
            for sequence in sequences:
                relation = {
                    "source": merged["object_id"],
                    "predicate": "has_sequence",
                    "target": sequence["object_id"],
                    "label": sequence["sequence_id"],
                    "evidence": merged["evidence_records"][0],
                    "source_dataset": sequence["dataset"],
                    "status": "active",
                }
                relations.append(relation)
                existing_relations.append(relation)
            merged["related_objects"] = existing_relations
        genes.append(merged)

    species_record = {
        "object_type": "Species",
        "object_id": f"species:{species_id}",
        "id": species_id,
        "name": species_name,
        "description": f"PhytoAtlas normalized species record for {species_name}.",
        "datasets": [dataset["object_id"] for dataset in gene_tsv_result.datasets],
        "updated_at": updated_at,
    }
    sequence_records = [sequence for result in fasta_results for sequence in result.sequence_records]
    datasets = gene_tsv_result.datasets + [dataset for result in fasta_results for dataset in result.datasets]
    gene_locations = gff_result.gene_locations if gff_result else []
    gene_structures = gff_result.gene_structures if gff_result else []
    if gff_result:
        datasets.extend(gff_result.datasets)
        relations.extend(gff_result.relations)
    for fasta_result in fasta_results:
        relations.extend(fasta_result.relations)

    write_jsonl(output_path / "species.jsonl", [species_record])
    write_jsonl(output_path / "genes.jsonl", genes)
    write_jsonl(output_path / "datasets.jsonl", datasets)
    write_jsonl(output_path / "sequence_records.jsonl", sequence_records)
    write_jsonl(output_path / "gene_locations.jsonl", gene_locations)
    write_jsonl(output_path / "gene_structures.jsonl", gene_structures)
    write_jsonl(output_path / "relations.jsonl", relations)
    write_jsonl(output_path / "evidence_claims.jsonl", gene_tsv_result.evidence_claims)

    manifest = {
        "species_id": species_id,
        "species_name": species_name,
        "output_dir": str(output_path),
        "counts": {
            "species": 1,
            "genes": len(genes),
            "datasets": len(datasets),
            "sequence_records": len(sequence_records),
            "gene_locations": len(gene_locations),
            "gene_structures": len(gene_structures),
            "relations": len(relations),
            "evidence_claims": len(gene_tsv_result.evidence_claims),
        },
    }
    (output_path / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def _base_gene_key(gene_id: str) -> str:
    value = gene_id.rsplit(":", 1)[-1]
    value = value.replace("gene:", "")
    for marker in (".1.v", ".2.v", ".3.v", ".v"):
        if marker in value:
            return value.split(marker, 1)[0]
    return value


def _sequence_type_from_path(path: Path) -> str:
    lowered = path.name.lower()
    if ".cds" in lowered:
        return "CDS"
    if ".pep" in lowered or "protein" in lowered:
        return "protein"
    if ".genomic" in lowered:
        return "genomic"
    return "sequence"
