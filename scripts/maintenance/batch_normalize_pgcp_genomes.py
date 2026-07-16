#!/usr/bin/env python3
"""Batch-normalize PGCP genome directories into PhytoAtlas JSONL graph objects."""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from phytoatlas.normalize.pipeline import build_minimal_species_knowledge_base  # noqa: E402

DEFAULT_INPUT_ROOT = Path("/DATA/data2/genomes")
DEFAULT_OUTPUT_ROOT = Path("/DATA/data2/phytoatlas/processed/pgcp_v1")


def iter_pgcp_species_dirs(input_root: Path):
    yield from sorted(input_root.glob("*/PGCP/v1"), key=lambda path: path.parent.parent.name.lower())


def species_id_from_dir(species_dir: Path) -> str:
    return species_dir.parent.parent.name.lower().replace(" ", "_")


def discover_inputs(species_dir: Path) -> dict:
    species_name = species_dir.parent.parent.name
    species_id = species_id_from_dir(species_dir)
    prefix = species_id
    return {
        "species_name": species_name,
        "species_id": species_id,
        "gene_tsv": species_dir / f"{prefix}.gene.tsv",
        "gff": species_dir / f"{prefix}.genomic.gff.gz",
        "cds": species_dir / f"{prefix}.cds.fa.gz",
        "pep": species_dir / f"{prefix}.pep.fa.gz",
        "genomic_fasta": species_dir / f"{prefix}.genomic.fa.gz",
    }


def validate_inputs(inputs: dict, include_genomic_fasta: bool) -> list[str]:
    required = ["gene_tsv", "gff", "cds", "pep"]
    if include_genomic_fasta:
        required.append("genomic_fasta")
    return [key for key in required if not inputs[key].exists()]


def write_jsonl_append(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def output_complete(output_dir: Path) -> bool:
    manifest = output_dir / "manifest.json"
    if not manifest.exists():
        return False
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    counts = data.get("counts", {})
    return bool(counts.get("genes")) and bool((output_dir / "genes.jsonl").exists())


def normalize_one_species(
    *,
    species_dir: Path,
    output_root: Path,
    include_genomic_fasta: bool,
    overwrite: bool,
    updated_at: str,
) -> dict:
    inputs = discover_inputs(species_dir)
    missing = validate_inputs(inputs, include_genomic_fasta)
    output_dir = output_root / inputs["species_id"]

    if missing:
        return {
            "status": "missing_inputs",
            "species_name": inputs["species_name"],
            "species_id": inputs["species_id"],
            "species_dir": str(species_dir),
            "missing": missing,
        }

    if not overwrite and output_complete(output_dir):
        existing_manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
        return {
            "status": "skipped_existing",
            "species_name": inputs["species_name"],
            "species_id": inputs["species_id"],
            "species_dir": str(species_dir),
            "output_dir": str(output_dir),
            "counts": existing_manifest.get("counts", {}),
        }

    fasta_paths = [inputs["cds"], inputs["pep"]]
    if include_genomic_fasta:
        fasta_paths.append(inputs["genomic_fasta"])

    manifest = build_minimal_species_knowledge_base(
        species_name=inputs["species_name"],
        species_id=inputs["species_id"],
        fasta_paths=fasta_paths,
        gff_path=inputs["gff"],
        gene_tsv_path=inputs["gene_tsv"],
        output_dir=output_dir,
        source_provider="PGCP",
        import_batch="pgcp_v1",
        version="v1",
        assembly="PGCP_v1",
        updated_at=updated_at,
    )
    return {
        "status": "normalized",
        "species_name": inputs["species_name"],
        "species_id": inputs["species_id"],
        "species_dir": str(species_dir),
        "output_dir": str(output_dir),
        "counts": manifest.get("counts", {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--include-genomic-fasta", action="store_true")
    parser.add_argument("--updated-at", default=date.today().isoformat())
    args = parser.parse_args()

    species_dirs = list(iter_pgcp_species_dirs(args.input_root))
    selected = species_dirs[args.offset :]
    if args.limit is not None:
        selected = selected[: args.limit]

    args.output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_root / "batch_manifest.jsonl"
    error_path = args.output_root / "batch_errors.jsonl"

    summary = {
        "total_discovered": len(species_dirs),
        "selected": len(selected),
        "normalized": 0,
        "skipped_existing": 0,
        "missing_inputs": 0,
        "failed": 0,
    }

    for index, species_dir in enumerate(selected, start=args.offset + 1):
        try:
            record = normalize_one_species(
                species_dir=species_dir,
                output_root=args.output_root,
                include_genomic_fasta=args.include_genomic_fasta,
                overwrite=args.overwrite,
                updated_at=args.updated_at,
            )
            record["index"] = index
            summary[record["status"]] = summary.get(record["status"], 0) + 1
            write_jsonl_append(manifest_path, record)
            print(json.dumps(record, ensure_ascii=False), flush=True)
        except Exception as exc:  # noqa: BLE001 - batch runner must continue.
            summary["failed"] += 1
            error_record = {
                "status": "failed",
                "index": index,
                "species_dir": str(species_dir),
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
            write_jsonl_append(error_path, error_record)
            print(json.dumps(error_record, ensure_ascii=False), flush=True)

    summary_path = args.output_root / "batch_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": summary, "summary_path": str(summary_path)}, ensure_ascii=False), flush=True)
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
