"""MSA visualization using pyMSAviz."""

import argparse
import logging
from pathlib import Path
from typing import Optional

from pymsaviz import MsaViz

logger = logging.getLogger(__name__)

# Default color schemes per sequence type
_COLOR_SCHEME = {
    "dna": "Nucleotide",
    "rna": "Nucleotide",
    "protein": "Clustal",
    "auto": "Identity",
}


def visualize(
    aligned_fasta: str,
    output_file: Optional[str] = None,
    color_scheme: Optional[str] = None,
    seq_type: str = "auto",
    wrap_length: int = 80,
    show_consensus: bool = True,
    show_count: bool = True,
    force: bool = False,
) -> str:
    """Render MSA as PDF/PNG using pyMSAviz.

    Args:
        color_scheme: Override color scheme. If None, auto-selected by seq_type.
                      DNA/RNA: 'Nucleotide'; Protein: 'Clustal'; Other: 'Identity'.
        seq_type:     Used for auto color scheme selection ('dna', 'rna', 'protein', 'auto').
        wrap_length:  Number of alignment columns per row (default: 80).
    """
    input_path = Path(aligned_fasta)
    output_path = Path(output_file) if output_file else input_path.with_suffix(".pdf")

    if output_path.exists() and not force:
        logger.info(f"Output exists, skipping: {output_path}")
        return str(output_path)

    scheme = color_scheme or _COLOR_SCHEME.get(seq_type, "Identity")

    mv = MsaViz(
        str(input_path),
        color_scheme=scheme,
        wrap_length=wrap_length,
        show_consensus=show_consensus,
        show_count=show_count,
    )
    mv.savefig(str(output_path))
    logger.info(f"Saved MSA PDF: {output_path} (color_scheme={scheme})")
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(
        description="MSA visualization using pyMSAviz",
        epilog="""
Color scheme options:
  auto        Identity (default, works for any sequence type)
  Nucleotide  Color by nucleotide identity (DNA/RNA)
  Clustal     Clustal color scheme (protein, recommended)
  Zappo       Zappo physicochemical properties (protein)
  Taylor      Taylor color scheme (protein)
  Identity    Percent identity shading (universal)
  None        No coloring
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-i", "--input", required=True, help="Aligned FASTA")
    parser.add_argument("-o", "--output", default=None, help="Output PDF/PNG (default: input.pdf)")
    parser.add_argument(
        "--seq-type", default="auto", choices=["auto", "dna", "rna", "protein"],
        help="Sequence type for auto color scheme selection (default: auto)",
    )
    parser.add_argument("--color-scheme", default=None, help="Override color scheme")
    parser.add_argument("--wrap-length", type=int, default=80, help="Columns per row (default: 80)")
    parser.add_argument("--no-consensus", action="store_true", help="Hide consensus row")
    parser.add_argument("--no-count", action="store_true", help="Hide column count")
    parser.add_argument("-f", "--force", action="store_true", help="Overwrite existing output")
    args = parser.parse_args()

    visualize(
        args.input, args.output, args.color_scheme, args.seq_type,
        args.wrap_length, not args.no_consensus, not args.no_count, args.force,
    )


if __name__ == "__main__":
    main()
