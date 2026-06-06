#!/usr/bin/env python3
"""MSA pipeline: MAFFT → trimAl → IQ-TREE + visualization."""

import argparse
import logging
from pathlib import Path
from typing import Optional

from .msa_align import msa, detect_species, detect_seq_type, MAFFT_ALGOS
from .msa_trim import trim_alignment
from .msa_tree_build import build_tree
from .msa_view import visualize
from .msa_tree_view import visualize_tree

logger = logging.getLogger(__name__)


def pipeline(
    input_fasta: str,
    output_dir: Optional[str] = None,
    threads: int = 4,
    bootstrap: int = 0,
    trim_mode: str = "automated1",
    build_phylo: Optional[bool] = None,
    visualize_output: bool = True,
    force: bool = False,
    seq_type: str = "auto",
    algo: str = "auto",
    model: str = "TEST",
    clean: bool = False,
) -> dict:
    """Run the full MSA pipeline and return paths to all output files.

    Args:
        input_fasta:      Input FASTA file (DNA, RNA, or protein).
        output_dir:       Output directory (default: same directory as input).
        threads:          CPU threads for MAFFT and IQ-TREE.
        bootstrap:        UFBoot replicates for IQ-TREE (>= 1000 to enable).
        trim_mode:        trimAl trimming strategy.
        build_phylo:      Build phylogenetic tree. None = auto-detect from species count.
        visualize_output: Generate MSA PDF and tree PNG.
        force:            Overwrite existing output files.
        seq_type:         Sequence type: 'dna', 'rna', 'protein', or 'auto'.
        algo:             MAFFT algorithm (see msa_align.MAFFT_ALGOS).
        model:            IQ-TREE substitution model (default: TEST = auto-select).
        clean:            Remove IQ-TREE intermediate files after tree building.

    Returns:
        dict with keys: aligned, trimmed, and optionally msa_pdf, treefile, tree_png.
    """
    input_path = Path(input_fasta)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = input_path.stem
    aligned = out_dir / f"{stem}.aligned.fasta"
    trimmed = out_dir / f"{stem}.trimmed.fasta"
    msa_pdf = out_dir / f"{stem}.msa.pdf"
    tree_prefix = str(out_dir / stem)
    tree_png = out_dir / f"{stem}.tree.png"

    # Auto-detect sequence type for downstream tool configuration
    effective_seq_type = seq_type if seq_type != "auto" else detect_seq_type(str(input_path))
    logger.info(f"Sequence type: {effective_seq_type}")

    # Auto-detect whether to build a phylogenetic tree
    if build_phylo is None:
        species = detect_species(str(input_path))
        build_phylo = len(species) > 1
        logger.info(f"Detected {len(species)} species {species}, tree: {build_phylo}")

    # Step 1: MAFFT alignment
    logger.info(f"[1/3] MAFFT: {input_path} -> {aligned}")
    msa(str(input_path), str(aligned), threads, force, effective_seq_type, algo)

    # Step 2: trimAl trimming
    logger.info(f"[2/3] trimAl ({trim_mode}): {aligned} -> {trimmed}")
    trim_alignment(str(aligned), str(trimmed), trim_mode, force)

    result = {"aligned": str(aligned), "trimmed": str(trimmed)}

    # Step 3: MSA visualization
    if visualize_output:
        logger.info(f"[3/3] MSA visualization -> {msa_pdf}")
        visualize(str(trimmed), str(msa_pdf), seq_type=effective_seq_type, force=force)
        result["msa_pdf"] = str(msa_pdf)

    # Step 4: Tree building + visualization
    if build_phylo:
        logger.info(f"[+] IQ-TREE ({model}): {trimmed}")
        treefile = build_tree(
            str(trimmed), tree_prefix, model=model,
            threads=threads, bootstrap=bootstrap, force=force, clean=clean,
        )
        result["treefile"] = treefile
        if visualize_output:
            visualize_tree(treefile, str(tree_png))
            result["tree_png"] = str(tree_png)

    return result


def main():
    parser = argparse.ArgumentParser(description="MSA pipeline: MAFFT → trimAl → IQ-TREE")
    parser.add_argument("-i", "--input", required=True, help="Input FASTA")
    parser.add_argument("-o", "--output-dir", default=None, help="Output directory")
    parser.add_argument("--threads", type=int, default=4, help="Threads (default: 4)")
    parser.add_argument("-bb", "--bootstrap", type=int, default=0,
                        help="UFBoot replicates (>= 1000 to enable)")
    parser.add_argument("-m", "--trim-mode", default="automated1",
                        choices=["automated1", "strict", "strictplus", "gappyout", "gt90"],
                        help="trimAl mode (default: automated1)")
    parser.add_argument("--tree", action="store_true",
                        help="Force tree building (overrides auto-detect)")
    parser.add_argument("--no-viz", action="store_true", help="Skip visualization")
    parser.add_argument("-f", "--force", action="store_true", help="Overwrite existing files")
    parser.add_argument("--seq-type", default="auto",
                        choices=["auto", "dna", "rna", "protein"],
                        help="Sequence type (default: auto-detect)")
    parser.add_argument("--algo", default="auto", choices=sorted(MAFFT_ALGOS),
                        help="MAFFT algorithm (default: auto)")
    parser.add_argument("--model", default="TEST",
                        help="IQ-TREE substitution model (default: TEST)")
    parser.add_argument("--clean", action="store_true",
                        help="Remove IQ-TREE intermediate files after completion")
    args = parser.parse_args()

    build_phylo = True if args.tree else None

    try:
        result = pipeline(
            args.input, args.output_dir, args.threads, args.bootstrap,
            args.trim_mode, build_phylo, not args.no_viz, args.force,
            args.seq_type, args.algo, args.model, args.clean,
        )
        print("\n[OK] Pipeline complete:")
        for key, path in result.items():
            print(f"  {key:<12} {path}")
    except Exception as e:
        logger.error(f"Failed: {e}")
        raise


if __name__ == "__main__":
    main()
