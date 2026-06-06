#!/usr/bin/env python3
"""Phylogenetic tree visualization using Biopython + Matplotlib."""

import argparse
import logging
from pathlib import Path
from Bio import Phylo
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


def visualize_tree(tree_file: str, output_png: str = None, show_bootstrap: bool = False):
    tree = Phylo.read(tree_file, "newick")
    output_path = Path(output_png) if output_png else Path(tree_file).with_suffix(".png")

    fig, ax = plt.subplots(figsize=(20, 14))

    # Format: SpeciesName|GeneID|TranscriptID -> show species + short gene ID
    def get_label(node):
        if not node.name:
            return ""
        parts = node.name.split("|")
        species = parts[0] if len(parts) > 0 else ""
        # Extract gene ID without IMPANE1G, IMPASA1G, IMPGACAM1N prefixes
        gene_full = parts[1] if len(parts) > 1 else ""
        gene_short = gene_full.replace("IMPANE1G", "G").replace("IMPASA1G", "G").replace("IMPGACAM1N", "N")
        return f"{species} {gene_short}"

    Phylo.draw(tree, axes=ax, show_confidence=show_bootstrap, label_func=get_label,
               branch_labels=lambda x: f"{x.branch_length:.3f}" if x.branch_length else "")

    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    logger.info(f"Saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Phylogenetic tree visualization")
    parser.add_argument("-i", "--input", required=True, help="Tree file (Newick)")
    parser.add_argument("-o", "--output", default=None, help="Output PNG")
    parser.add_argument("--bootstrap", action="store_true", help="Show bootstrap values")
    args = parser.parse_args()

    visualize_tree(args.input, args.output, args.bootstrap)


if __name__ == "__main__":
    main()