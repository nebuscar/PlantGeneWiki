#!/usr/bin/env python3
"""MSA alignment trimming using trimAl."""

import argparse
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def trim_alignment(input_fasta: str, output_fasta: str = None, mode: str = "automated1", force: bool = False):
    input_path = Path(input_fasta)
    output_path = Path(output_fasta) if output_fasta else input_path.with_suffix(".trimmed.fasta")

    if output_path.exists() and not force:
        logger.info(f"Output exists, skipping: {output_path}")
        return str(output_path)

    cmd = ["trimal", "-in", str(input_path), "-out", str(output_path), f"-{mode}"]
    logger.info(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"trimal failed: {result.stderr}")
        logger.info(f"Saved: {output_path}")
        return str(output_path)
    except Exception as e:
        raise RuntimeError(f"trimal error: {e}")


def main():
    parser = argparse.ArgumentParser(description="MSA trimming using trimAl")
    parser.add_argument("-i", "--input", required=True, help="Aligned FASTA")
    parser.add_argument("-o", "--output", default=None, help="Output trimmed FASTA")
    parser.add_argument("-m", "--mode", default="automated1",
                        choices=["automated1", "strict", "strictplus", "gappyout", "gt90"],
                        help="Trimming mode (default: automated1)")
    parser.add_argument("-f", "--force", action="store_true", help="Overwrite")
    args = parser.parse_args()

    try:
        result = trim_alignment(args.input, args.output, args.mode, args.force)
        print(f"\n[OK] Done: {result}")
    except Exception as e:
        logger.error(f"Failed: {e}")
        raise


if __name__ == "__main__":
    main()