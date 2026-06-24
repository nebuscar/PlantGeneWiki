#!/usr/bin/env python3
"""MSA alignment using MAFFT with support for DNA, RNA, and protein sequences."""

import argparse
import os
import subprocess
import logging
from pathlib import Path
from typing import Optional

from Bio import SeqIO

logger = logging.getLogger(__name__)

# Characters exclusive to each sequence type (after removing gaps/ambiguity)
_DNA_ONLY = set("T")
_RNA_ONLY = set("U")
_PROTEIN_ONLY = set("DEFHIKLMPQRSVWY")  # not in any nucleotide alphabet

MAFFT_ALGOS = frozenset({"auto", "linsi", "ginsi", "einsi", "fftnsi", "fftns", "nwnsi", "nwns"})

SEQ_TYPE_HINT = """
Supported sequence types:
  dna     – DNA nucleotide sequences (A/T/C/G)
  rna     – RNA sequences (A/U/C/G)
  protein – Amino acid sequences (20 standard + ambiguity codes)
  auto    – Auto-detect from sequence content (default)

Input format: standard FASTA (.fa, .fasta, .fna, .faa)
  - At least 2 sequences required
  - Sequences should be unaligned (gaps will be inserted by MAFFT)
  - Sequence IDs used for species detection:
      Genus_species|GeneID     →  Genus_species
      Genus_species_GeneID     →  Genus_species
      GENEID00001234           →  GENEID00001234
"""


def detect_seq_type(fasta: str) -> str:
    """Auto-detect sequence type from FASTA content.

    Samples up to 5 sequences and inspects their character composition.
    Returns 'dna', 'rna', or 'protein'.
    """
    chars: set[str] = set()
    for i, record in enumerate(SeqIO.parse(fasta, "fasta")):
        if i >= 5:
            break
        chars.update(str(record.seq).upper())

    # Strip gap/unknown characters that appear in all types
    chars -= set("-. NX")

    if not chars:
        return "dna"  # empty or all-N fallback

    if chars & _PROTEIN_ONLY:
        return "protein"
    if chars & _RNA_ONLY:
        return "rna"
    return "dna"


def _extract_species(name: str) -> str:
    """Extract species name from a sequence ID.

    Handles three formats:
    - 'Genus_species|GeneID...' -> 'Genus_species'
    - 'Genus_species_GeneID'    -> 'Genus_species'
    - 'GENEID00000001234'       -> 'GENEID00000001234'
    """
    if "|" in name:
        return name.split("|")[0]
    parts = name.split("_")
    # Species name: Genus (capital) + epithet (lowercase)
    if len(parts) >= 2 and parts[0][0].isupper() and parts[1][0].islower():
        return f"{parts[0]}_{parts[1]}"
    return name


def detect_species(fasta: str) -> list:
    """Return sorted list of unique species names detected in a FASTA file."""
    return sorted({_extract_species(r.id) for r in SeqIO.parse(fasta, "fasta")})


def validate_input(fasta_path: str) -> dict:
    """Validate FASTA input and return summary info.

    Raises FileNotFoundError, ValueError with user-friendly messages.
    Returns dict with keys: count, min_len, max_len, seq_type.
    """
    if not os.path.exists(fasta_path):
        raise FileNotFoundError(
            f"Input file not found: {fasta_path}\n{SEQ_TYPE_HINT}"
        )

    try:
        records = [r for r in SeqIO.parse(fasta_path, "fasta") if len(r.seq) > 0]
    except Exception as e:
        raise ValueError(
            f"Failed to parse FASTA file: {e}\n"
            "Make sure the file is in valid FASTA format.\n"
            f"{SEQ_TYPE_HINT}"
        ) from e

    if not records:
        raise ValueError(
            f"No valid sequences found in: {fasta_path}\n"
            "File must be non-empty FASTA with at least 2 sequences.\n"
            f"{SEQ_TYPE_HINT}"
        )

    if len(records) < 2:
        raise ValueError(
            f"At least 2 sequences required, got {len(records)} in: {fasta_path}\n"
            "MSA requires multiple sequences to align."
        )

    lengths = [len(r.seq) for r in records]
    seq_type = detect_seq_type(fasta_path)
    min_warn = 50 if seq_type == "protein" else 100

    if min(lengths) < min_warn:
        logger.warning(
            f"Shortest sequence is {min(lengths)} chars — "
            f"very short {seq_type} sequences may produce unreliable alignments."
        )

    return {
        "count": len(records),
        "min_len": min(lengths),
        "max_len": max(lengths),
        "seq_type": seq_type,
    }


def run_mafft(
    input_fasta: str,
    output_fasta: str,
    threads: int = 4,
    seq_type: str = "auto",
    algo: str = "auto",
) -> dict:
    """Run MAFFT alignment.

    Args:
        seq_type: 'dna', 'rna', 'protein', or 'auto' (MAFFT auto-detects).
        algo:     MAFFT algorithm: 'auto', 'linsi', 'ginsi', 'einsi',
                  'fftnsi', 'fftns', 'nwnsi', 'nwns'.
                  'linsi' is most accurate but slowest; 'fftns' is fastest.
    """
    cmd = ["mafft", "--quiet", "--thread", str(threads)]

    if algo != "auto" and algo in MAFFT_ALGOS:
        _algo_map = {
            "linsi":   ["--maxiterate", "1000", "--localpair"],
            "ginsi":   ["--maxiterate", "1000", "--globalpair"],
            "einsi":   ["--maxiterate", "1000", "--genafpair"],
            "fftnsi":  ["--maxiterate", "1000", "--nwnsi"],
            "fftns":   ["--retree", "1"],
            "nwnsi":   ["--maxiterate", "1000", "--nwnsni"],
            "nwns":    ["--retree", "1"],
        }
        if algo in _algo_map:
            cmd.extend(_algo_map[algo])
        else:
            cmd.append(f"--{algo}")

    if seq_type in ("dna", "rna"):
        cmd.append("--nuc")
    elif seq_type == "protein":
        cmd.append("--amino")
    # else: let MAFFT auto-detect

    cmd.append(input_fasta)

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"MAFFT failed:\n{result.stderr.decode()}")
    Path(output_fasta).write_bytes(result.stdout)

    records = list(SeqIO.parse(output_fasta, "fasta"))
    return {"sequences": len(records), "length": len(records[0].seq) if records else 0}


def msa(
    input_fasta: str,
    output_fasta: Optional[str] = None,
    threads: int = 4,
    force: bool = False,
    seq_type: str = "auto",
    algo: str = "auto",
) -> str:
    """Align sequences with MAFFT and return path to aligned FASTA."""
    input_path = Path(input_fasta)
    output_path = Path(output_fasta) if output_fasta else input_path.with_suffix(".aligned.fasta")

    if output_path.exists() and not force:
        logger.info(f"Output exists, skipping: {output_path}")
        return str(output_path)

    info = validate_input(str(input_path))
    detected = info["seq_type"]
    effective_type = seq_type if seq_type != "auto" else detected
    logger.info(
        f"Input: {input_path} | {info['count']} seqs | "
        f"len {info['min_len']}–{info['max_len']} | type: {effective_type}"
    )

    result = run_mafft(str(input_path), str(output_path), threads, effective_type, algo)
    logger.info(f"Aligned: {output_path} | {result['sequences']} seqs | {result['length']} cols")

    return str(output_path)


def main():
    parser = argparse.ArgumentParser(
        description="MSA alignment using MAFFT",
        epilog=SEQ_TYPE_HINT,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-i", "--input", required=True, help="Input FASTA")
    parser.add_argument("-o", "--output", default=None, help="Output aligned FASTA")
    parser.add_argument("--threads", type=int, default=4, help="Threads (default: 4)")
    parser.add_argument(
        "--seq-type", default="auto", choices=["auto", "dna", "rna", "protein"],
        help="Sequence type (default: auto-detect)",
    )
    parser.add_argument(
        "--algo", default="auto", choices=sorted(MAFFT_ALGOS),
        help="MAFFT algorithm (default: auto; linsi=most accurate, fftns=fastest)",
    )
    parser.add_argument("-f", "--force", action="store_true", help="Overwrite existing output")
    args = parser.parse_args()

    try:
        result = msa(args.input, args.output, args.threads, args.force, args.seq_type, args.algo)
        print(f"\n[OK] Done: {result}")
    except Exception as e:
        logger.error(f"Failed: {e}")
        raise


if __name__ == "__main__":
    main()
