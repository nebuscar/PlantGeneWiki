#!/usr/bin/env python3
"""
ESMFold protein structure prediction CLI.

MUST be run with the esmfold conda environment:
  /home/nizhu/software/miniforge3/envs/esmfold/bin/python esmfold_predict.py [options]

Or activate the environment first:
  conda activate esmfold && python esmfold_predict.py [options]

Usage:
  # From sequence string
  python esmfold_predict.py -s MKTAYIAKQRQISFVK... -o output/

  # From FASTA file (single sequence)
  python esmfold_predict.py -i protein.faa -o output/

  # From FASTA file (all sequences, batch mode)
  python esmfold_predict.py -i proteins.faa -o output/ --batch

  # Higher accuracy (slower)
  python esmfold_predict.py -i protein.faa -o output/ --num-recycles 8
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# esmfold_model.py applies the CUDA patch at import time
from esmfold_model import (
    clean_sequence,
    parse_fasta_or_seq,
    plot_plddt,
    predict,
    INPUT_FORMAT_HINT,
    MAX_SEQ_LEN,
    MIN_SEQ_LEN,
)


def _parse_fasta_multi(path: str) -> list[tuple[str, str]]:
    """Parse a multi-sequence FASTA file. Returns list of (name, seq)."""
    entries = []
    name, seq_parts = None, []
    for line in Path(path).read_text().splitlines():
        if line.startswith(">"):
            if name is not None:
                entries.append((name, "".join(seq_parts)))
            name = line[1:].split()[0]
            seq_parts = []
        elif line.strip():
            seq_parts.append(line.strip())
    if name is not None:
        entries.append((name, "".join(seq_parts)))
    return entries


def _run_single(
    name: str,
    raw_seq: str,
    output_dir: Path,
    num_recycles: int,
    chunk_size: Optional[int],
    no_plot: bool,
    force: bool,
) -> dict:
    """Run prediction for one sequence and return result dict."""
    pdb_path  = output_dir / f"{name}.pdb"
    json_path = output_dir / f"{name}.json"
    png_path  = output_dir / f"{name}.plddt.png"

    if pdb_path.exists() and not force:
        logger.info(f"Skipping (exists): {pdb_path}")
        if json_path.exists():
            return json.loads(json_path.read_text())
        return {"pdb": str(pdb_path), "skipped": True}

    try:
        seq = clean_sequence(raw_seq)
    except ValueError as e:
        logger.error(f"[{name}] Invalid sequence: {e}")
        return {"name": name, "error": str(e)}

    result = predict(seq, str(pdb_path), num_recycles=num_recycles, chunk_size=chunk_size)
    result["name"] = name
    result["sequence"] = seq

    # pLDDT plot
    if not no_plot:
        plot_plddt(result["plddt_per_residue"], str(png_path), protein_name=name)
        result["plddt_png"] = str(png_path)

    # JSON summary
    json_path.write_text(json.dumps(result, indent=2))
    result["json"] = str(json_path)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="ESMFold protein structure prediction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=INPUT_FORMAT_HINT + """
Examples:
  # Single sequence string
  python esmfold_predict.py -s MKTAYIAKQRQISFVKSHFSRQLEERLGLIEV -o out/

  # From FASTA file
  python esmfold_predict.py -i gene.faa -o out/

  # Batch mode (all sequences in FASTA)
  python esmfold_predict.py -i proteins.faa -o out/ --batch

  # Higher accuracy
  python esmfold_predict.py -i protein.faa -o out/ --num-recycles 8

  # Memory-constrained (chunk attention)
  python esmfold_predict.py -i protein.faa -o out/ --chunk-size 64
        """,
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("-s", "--sequence", metavar="SEQ",
                             help="Amino acid sequence string (plain or FASTA format)")
    input_group.add_argument("-i", "--input", metavar="FASTA",
                             help="Input FASTA file")

    parser.add_argument("-o", "--output", default=".", metavar="DIR",
                        help="Output directory (default: current directory)")
    parser.add_argument("-n", "--name", default=None,
                        help="Output file stem (default: from FASTA header or 'protein')")
    parser.add_argument("--batch", action="store_true",
                        help="Process all sequences in FASTA file (requires --input)")
    parser.add_argument(
        "--num-recycles", type=int, default=4, metavar="N",
        help="Recycling iterations (default: 4, range: 1–20; more = more accurate but slower)",
    )
    parser.add_argument(
        "--chunk-size", type=int, default=None, metavar="N",
        help="Attention chunk size to reduce memory (e.g. 64, 128; default: None = no chunking)",
    )
    parser.add_argument("--no-plot", action="store_true",
                        help="Skip pLDDT confidence plot generation")
    parser.add_argument("-f", "--force", action="store_true",
                        help="Overwrite existing output files")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []

    if args.sequence:
        # Single sequence from command line
        name, raw_seq = parse_fasta_or_seq(args.sequence)
        name = args.name or name
        result = _run_single(name, raw_seq, output_dir, args.num_recycles,
                             args.chunk_size, args.no_plot, args.force)
        results.append(result)

    elif args.batch:
        # Batch mode: all sequences in FASTA
        entries = _parse_fasta_multi(args.input)
        logger.info(f"Batch mode: {len(entries)} sequences")
        for name, raw_seq in entries:
            result = _run_single(name, raw_seq, output_dir, args.num_recycles,
                                 args.chunk_size, args.no_plot, args.force)
            results.append(result)

    else:
        # Single sequence from FASTA file (first sequence)
        entries = _parse_fasta_multi(args.input)
        if not entries:
            logger.error(f"No sequences found in {args.input}")
            sys.exit(1)
        name, raw_seq = entries[0]
        name = args.name or name
        if len(entries) > 1:
            logger.warning(f"FASTA contains {len(entries)} sequences; using first only. Use --batch for all.")
        result = _run_single(name, raw_seq, output_dir, args.num_recycles,
                             args.chunk_size, args.no_plot, args.force)
        results.append(result)

    # Print summary
    print("\n[OK] Prediction complete:")
    for r in results:
        if "error" in r:
            print(f"  {r.get('name', '?'):30s}  ERROR: {r['error']}")
            continue
        print(f"  {r.get('name', '?'):30s}  "
              f"pLDDT={r.get('mean_plddt', '?'):5.1f}  "
              f"pTM={r.get('ptm', '?')!s:6s}  "
              f"len={r.get('seq_len', '?'):4d}  "
              f"time={r.get('inference_time_s', '?'):.0f}s  "
              f"→  {r.get('pdb', '')}")


if __name__ == "__main__":
    main()
