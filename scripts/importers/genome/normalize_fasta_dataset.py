#!/usr/bin/env python3
"""Normalize one FASTA/FASTA.GZ file into PhytoAtlas JSONL objects."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from phytoatlas.normalize.fasta import normalize_fasta_dataset, write_normalized_fasta_outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Input FASTA or FASTA.GZ file")
    parser.add_argument("--output", required=True, type=Path, help="Output directory for JSONL and summary files")
    parser.add_argument("--species-name", required=True, help="Scientific species name, e.g. Abies alba")
    parser.add_argument("--species-id", required=True, help="Stable species id, e.g. abies_alba")
    parser.add_argument("--source", required=True, help="Data source, e.g. PGCP")
    parser.add_argument("--version", required=True, help="Source or annotation version, e.g. v1")
    parser.add_argument("--sequence-type", required=True, help="Sequence type, e.g. CDS or protein")
    args = parser.parse_args()

    result = normalize_fasta_dataset(
        input_path=args.input,
        species_name=args.species_name,
        species_id=args.species_id,
        source=args.source,
        version=args.version,
        sequence_type=args.sequence_type,
    )
    write_normalized_fasta_outputs(result, args.output)
    print(f"datasets: {len(result.datasets)}")
    print(f"sequence_records: {len(result.sequence_records)}")
    print(f"relations: {len(result.relations)}")
    print(f"output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
