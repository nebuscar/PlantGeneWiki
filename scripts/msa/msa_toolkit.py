#!/usr/bin/env python3
"""MSA toolkit CLI: MAFFT + trimAl + IQ-TREE + visualization.

Supports DNA, RNA, and protein sequences. Auto-detects sequence type and
builds a phylogenetic tree only when multiple species are detected.

Usage:
    # Auto mode: detect type + species, run appropriate pipeline
    python msa_toolkit.py -i input.fa -o output/

    # Force phylogenetic tree with bootstrap
    python msa_toolkit.py -i orthologs.fa -o output/ --tree --bootstrap 1000

    # Protein MSA with Clustal color scheme
    python msa_toolkit.py -i proteins.faa -o output/ --seq-type protein

    # Most accurate alignment (slow, for <200 sequences)
    python msa_toolkit.py -i input.fa -o output/ --algo linsi
"""

import argparse
import logging
from pathlib import Path

from msa_align import msa, detect_species, detect_seq_type, MAFFT_ALGOS, SEQ_TYPE_HINT
from msa_trim import trim_alignment
from msa_tree_build import build_tree
from msa_view import visualize
from msa_tree_view import visualize_tree

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="MSA toolkit: MAFFT + trimAl + IQ-TREE + visualization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=SEQ_TYPE_HINT + """
Examples:
  # Same-species MSA, auto-detected, no tree
  python msa_toolkit.py -i same_sp.fa -o out/

  # Multi-species phylogeny, auto-detected
  python msa_toolkit.py -i orthologs.fa -o out/

  # Protein sequences with bootstrap tree
  python msa_toolkit.py -i proteins.faa -o out/ --seq-type protein --tree --bootstrap 1000

  # Accurate alignment + explicit GTR model
  python msa_toolkit.py -i dna.fa -o out/ --algo linsi --model GTR+G

  # Keep only treefile (remove IQ-TREE log/checkpoint files)
  python msa_toolkit.py -i input.fa -o out/ --clean
        """,
    )

    # --- Input / Output ---
    io_group = parser.add_argument_group("Input / Output")
    io_group.add_argument("-i", "--input", required=True, metavar="FASTA",
                          help="Input FASTA file (DNA, RNA, or protein; unaligned)")
    io_group.add_argument("-o", "--output", default=".", metavar="DIR",
                          help="Output directory (default: current directory)")
    io_group.add_argument("-f", "--force", action="store_true",
                          help="Overwrite existing output files")

    # --- Sequence type ---
    seq_group = parser.add_argument_group("Sequence type")
    seq_group.add_argument(
        "--seq-type", default="auto", choices=["auto", "dna", "rna", "protein"],
        help="Sequence type (default: auto-detect from content)",
    )

    # --- MAFFT alignment ---
    mafft_group = parser.add_argument_group("MAFFT alignment")
    mafft_group.add_argument("--threads", type=int, default=4,
                             help="CPU threads for MAFFT and IQ-TREE (default: 4)")
    mafft_group.add_argument(
        "--algo", default="auto", choices=sorted(MAFFT_ALGOS),
        help=(
            "MAFFT algorithm (default: auto):\n"
            "  linsi  – most accurate, slowest (L-INS-i, best for <200 seqs)\n"
            "  ginsi  – global alignment, accurate\n"
            "  einsi  – for sequences with long unalignable regions\n"
            "  fftns  – fastest, lower accuracy (good for >1000 seqs)"
        ),
    )

    # --- trimAl trimming ---
    trim_group = parser.add_argument_group("trimAl trimming")
    trim_group.add_argument(
        "--trim-mode", default="automated1",
        choices=["automated1", "strict", "strictplus", "gappyout", "gt90"],
        help=(
            "trimAl trimming mode (default: automated1):\n"
            "  automated1  – auto-selects best strategy (recommended)\n"
            "  gappyout    – removes columns with high gap content\n"
            "  strict      – strict column filtering\n"
            "  gt90        – keep columns with >90%% residues present"
        ),
    )

    # --- Phylogeny ---
    tree_group = parser.add_argument_group("Phylogenetic tree (IQ-TREE)")
    tree_group.add_argument("--tree", action="store_true",
                            help="Force tree building (default: auto when >1 species detected)")
    tree_group.add_argument("--msa-only", action="store_true",
                            help="Skip tree building and tree visualization entirely")
    tree_group.add_argument(
        "--bootstrap", type=int, default=0, metavar="N",
        help="UFBoot replicates (must be >= 1000; 0 = off; recommended: 1000)",
    )
    tree_group.add_argument(
        "--model", default="TEST", metavar="MODEL",
        help=(
            "IQ-TREE substitution model (default: TEST = auto-select).\n"
            "DNA examples:     GTR+G, HKY+G\n"
            "Protein examples: LG+G, WAG+G, JTT+G"
        ),
    )
    tree_group.add_argument("--show-bootstrap", action="store_true",
                            help="Show bootstrap values on tree visualization")
    tree_group.add_argument("--clean", action="store_true",
                            help="Remove IQ-TREE intermediate files (.log, .ckp.gz, etc.)")

    # --- Visualization ---
    viz_group = parser.add_argument_group("Visualization")
    viz_group.add_argument("--color-scheme", default=None, metavar="SCHEME",
                           help="pyMSAviz color scheme override (default: auto by seq type)")
    viz_group.add_argument("--wrap-length", type=int, default=80,
                           help="MSA plot columns per row (default: 80)")
    viz_group.add_argument("--no-viz", action="store_true",
                           help="Skip all visualization (MSA PDF and tree PNG)")

    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = input_path.stem
    aligned_fasta = output_dir / f"{stem}.aligned.fasta"
    trimmed_fasta = output_dir / f"{stem}.trimmed.fasta"
    msa_pdf = output_dir / f"{stem}.msa.pdf"
    tree_prefix = str(output_dir / stem)
    tree_png = output_dir / f"{stem}.tree.png"

    try:
        # Step 1: Detect sequence type + species
        effective_seq_type = (
            args.seq_type if args.seq_type != "auto"
            else detect_seq_type(str(input_path))
        )
        species_list = detect_species(str(input_path))
        n_species = len(species_list)

        logger.info(f"Input:       {input_path}")
        logger.info(f"Seq type:    {effective_seq_type}")
        logger.info(f"Species ({n_species}): {species_list}")

        build_tree_flag = (
            not args.msa_only and (args.tree or n_species > 1)
        )

        # Step 2: MAFFT alignment
        logger.info("[1/3] MAFFT alignment...")
        msa(str(input_path), str(aligned_fasta), args.threads, args.force,
            effective_seq_type, args.algo)

        # Step 3: trimAl trimming
        logger.info(f"[2/3] trimAl trimming ({args.trim_mode})...")
        trim_alignment(str(aligned_fasta), str(trimmed_fasta), args.trim_mode, args.force)

        # Step 4: MSA visualization
        if not args.no_viz:
            logger.info("[3/3] MSA visualization...")
            visualize(
                str(trimmed_fasta), str(msa_pdf),
                color_scheme=args.color_scheme,
                seq_type=effective_seq_type,
                wrap_length=args.wrap_length,
                force=args.force,
            )
        else:
            logger.info("[3/3] Skipped visualization (--no-viz)")

        # Step 5: Tree building + tree visualization
        treefile_path = None
        if build_tree_flag:
            logger.info(f"[+] Building phylogenetic tree (model={args.model})...")
            treefile_path = build_tree(
                str(trimmed_fasta), tree_prefix,
                model=args.model, threads=args.threads,
                bootstrap=args.bootstrap, force=args.force, clean=args.clean,
            )
            if not args.no_viz:
                visualize_tree(treefile_path, str(tree_png), args.show_bootstrap)
        elif args.msa_only:
            logger.info("[+] Skipped tree building (--msa-only)")
        else:
            logger.info("[+] Skipped tree building (single species detected)")

        # Summary
        print("\n[OK] Complete!")
        print(f"  seq_type  : {effective_seq_type}")
        print(f"  species   : {n_species}")
        print(f"  aligned   : {aligned_fasta}")
        print(f"  trimmed   : {trimmed_fasta}")
        if not args.no_viz:
            print(f"  msa_pdf   : {msa_pdf}")
        if treefile_path:
            print(f"  treefile  : {treefile_path}")
            if not args.no_viz:
                print(f"  tree_png  : {tree_png}")

    except FileNotFoundError as e:
        logger.error(str(e))
        raise SystemExit(1)
    except ValueError as e:
        logger.error(str(e))
        raise SystemExit(1)
    except Exception as e:
        logger.error(f"Failed: {e}")
        raise


if __name__ == "__main__":
    main()
