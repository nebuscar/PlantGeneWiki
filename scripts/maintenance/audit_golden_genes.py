#!/usr/bin/env python3
"""Audit normalized species data against a golden gene contract."""

from __future__ import annotations

########## 0. imports ##########
import argparse
import json
from pathlib import Path
from typing import Sequence

from phytoatlas.quality.golden_gene_audit import audit_golden_genes


########## 1. cli ##########
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--species-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = audit_golden_genes(args.species_dir, args.manifest)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps({
        "species_id": report["species_id"],
        "status": report["status"],
        "golden_gene_count": report["golden_gene_count"],
        "passed_gene_count": report["passed_gene_count"],
    }, ensure_ascii=False, separators=(",", ":")))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
