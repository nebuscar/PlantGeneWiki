#!/usr/bin/env python3
"""Phylogenetic tree building using IQ-TREE."""

import argparse
import glob
import os
import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# IQ-TREE files that are safe to remove after the run (keep .treefile and .contree)
_IQTREE_INTERMEDIATES = {".iqtree", ".log", ".ckp.gz", ".bionj", ".mldist", ".model.gz"}


def _clean_intermediates(prefix: str) -> None:
    """Remove IQ-TREE intermediate files, keeping only treefile and contree."""
    kept, removed = 0, 0
    for path in glob.glob(f"{prefix}.*"):
        ext = "".join(Path(path).suffixes)
        if ext in _IQTREE_INTERMEDIATES:
            try:
                os.remove(path)
                removed += 1
            except OSError as e:
                logger.warning(f"Could not remove {path}: {e}")
        else:
            kept += 1
    logger.info(f"Cleanup: removed {removed} intermediate files, kept {kept}")


def build_tree(
    aligned_fasta: str,
    output_prefix: Optional[str] = None,
    model: str = "TEST",
    threads: int = 4,
    bootstrap: int = 0,
    force: bool = False,
    clean: bool = False,
) -> str:
    """Run IQ-TREE and return path to the resulting .treefile.

    Args:
        aligned_fasta:  Path to trimmed/aligned FASTA input.
        output_prefix:  Prefix for all IQ-TREE output files (e.g. 'out/gene1').
                        Defaults to input path (files placed beside input).
        model:          Substitution model. Use 'TEST' for auto model selection,
                        or explicit models e.g. 'GTR+G' (DNA), 'LG+G' (protein).
        threads:        CPU threads.
        bootstrap:      UFBoot replicates (must be >= 1000 to enable; 0 = off).
        force:          Re-run even if treefile already exists.
        clean:          Remove IQ-TREE log/.ckp/.iqtree intermediate files after run.
    """
    input_path = Path(aligned_fasta)
    prefix = output_prefix or str(input_path)
    treefile = Path(f"{prefix}.treefile")

    if treefile.exists() and not force:
        logger.info(f"Tree exists, skipping: {treefile}")
        return str(treefile)

    cmd = ["iqtree", "-s", str(input_path), "-pre", prefix, "-m", model, "-nt", str(threads)]
    if force:
        cmd.append("-redo")
    if bootstrap >= 1000:
        cmd.extend(["-bb", str(bootstrap)])
    elif bootstrap > 0:
        logger.warning(f"bootstrap={bootstrap} ignored — UFBoot requires >= 1000")

    logger.info(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        if result.returncode != 0:
            raise RuntimeError(f"IQ-TREE failed:\n{result.stderr}")
    except subprocess.TimeoutExpired:
        raise TimeoutError("IQ-TREE timed out after 1 hour")

    if clean:
        _clean_intermediates(prefix)

    logger.info(f"Saved: {treefile}")
    return str(treefile)


def main():
    parser = argparse.ArgumentParser(
        description="Phylogenetic tree using IQ-TREE",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Model examples:
  TEST          Auto model selection via ModelTest-NG (default, works for DNA & protein)
  GTR+G         General time-reversible + Gamma (DNA)
  GTR+G+ASC     GTR+Gamma with ascertainment bias correction
  LG+G          LG substitution matrix + Gamma (protein)
  WAG+G         WAG matrix + Gamma (protein)
  JTT+G         JTT matrix + Gamma (protein)
        """,
    )
    parser.add_argument("-i", "--input", required=True, help="Aligned/trimmed FASTA")
    parser.add_argument("-p", "--prefix", default=None,
                        help="Output prefix for all IQ-TREE files (default: input path)")
    parser.add_argument("-m", "--model", default="TEST",
                        help="Substitution model (default: TEST = auto-select)")
    parser.add_argument("--threads", type=int, default=4, help="Threads (default: 4)")
    parser.add_argument("-bb", "--bootstrap", type=int, default=0,
                        help="UFBoot replicates (must be >= 1000 to enable, 0 = off)")
    parser.add_argument("-f", "--force", action="store_true", help="Overwrite existing tree")
    parser.add_argument("--clean", action="store_true",
                        help="Remove IQ-TREE intermediate files after completion")
    args = parser.parse_args()

    try:
        result = build_tree(
            args.input, args.prefix, args.model, args.threads,
            args.bootstrap, args.force, args.clean,
        )
        print(f"\n[OK] Done: {result}")
    except Exception as e:
        logger.error(f"Failed: {e}")
        raise


if __name__ == "__main__":
    main()
