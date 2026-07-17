#!/usr/bin/env python3
"""Audit one normalized species directory against the PhytoAtlas MVP gate."""

from __future__ import annotations

########## 0. imports ##########
import argparse
import json
from pathlib import Path
from typing import Sequence

from phytoatlas.quality.species_audit import audit_species_directory


########## 1. cli ##########
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--species-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    report = audit_species_directory(args.species_dir)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(
        json.dumps(
            {
                "species_id": report["species_id"],
                "status": report["status"],
                "issue_count": len(report["issues"]),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
