"""Profile normalized genes for golden-manifest selection."""

from __future__ import annotations

########## 0. imports ##########
import argparse
import json
from pathlib import Path

from phytoatlas.quality.gene_profile import profile_gene_candidates


########## 1. arguments ##########
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--species-dir", required=True, type=Path)
    parser.add_argument("--limit", default=5, type=int)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


########## 2. main ##########
def main() -> int:
    args = parse_args()
    report = profile_gene_candidates(args.species_dir, limit=args.limit)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
