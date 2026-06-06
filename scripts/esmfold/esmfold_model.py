"""
ESMFold protein structure prediction — model layer.

Must be run inside the 'esmfold' conda environment:
  /home/nizhu/software/miniforge3/envs/esmfold/bin/python

The CUDA kernel patch (attn_core_inplace_cuda) must be applied at
module load time, before any ESM import. This file handles that automatically.
"""

from __future__ import annotations

# ── CUDA kernel patch (needed on systems with GLIBC < 2.34 or CPU-only) ────
import sys
import unittest.mock
sys.modules.setdefault("attn_core_inplace_cuda", unittest.mock.MagicMock())

import logging  # noqa: E402
import re  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Optional  # noqa: E402

import torch  # noqa: E402

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

ESMFOLD_PYTHON = "/home/nizhu/software/miniforge3/envs/esmfold/bin/python"

VALID_AA = set("ACDEFGHIKLMNPQRSTVWY")

# pLDDT confidence thresholds (AlphaFold2 convention)
PLDDT_VERY_HIGH = 90   # > 90: very high confidence
PLDDT_HIGH      = 70   # 70–90: high confidence
PLDDT_LOW       = 50   # 50–70: low confidence (use with caution)
                       # < 50: very low, likely disordered

MAX_SEQ_LEN = 800      # practical CPU limit (avoids OOM / multi-hour runs)
MIN_SEQ_LEN = 6

INPUT_FORMAT_HINT = """
Input requirements:
  - Single amino acid sequence (standard 20-letter code: ACDEFGHIKLMNPQRSTVWY)
  - Length: {min}–{max} residues
  - FASTA format or plain sequence string accepted
  - Non-standard residues (B, Z, X, U, O) are removed automatically

Sequence ID format in FASTA (for output naming):
  >ProteinName
  MKTAYIAKQRQIS...

Multimer prediction: separate chains with ':' (e.g. CHAIN_A:CHAIN_B)
""".format(min=MIN_SEQ_LEN, max=MAX_SEQ_LEN)

# ── Model singleton (loaded once per process) ────────────────────────────────

_model = None
_model_load_time: Optional[float] = None


def get_model():
    """Return the ESMFold model, loading it on first call (lazy singleton)."""
    global _model, _model_load_time
    if _model is None:
        import esm
        logger.info("Loading ESMFold v1 model (~3.5B params, first call may take 60s)...")
        t0 = time.time()
        _model = esm.pretrained.esmfold_v1().eval().float()
        _model_load_time = time.time() - t0
        logger.info(f"Model loaded in {_model_load_time:.1f}s")
    return _model


# ── Sequence utilities ───────────────────────────────────────────────────────

def parse_fasta_or_seq(text: str) -> tuple[str, str]:
    """Parse FASTA or plain sequence. Returns (name, cleaned_sequence)."""
    text = text.strip()
    if text.startswith(">"):
        lines = text.splitlines()
        name = lines[0][1:].split()[0]
        seq  = "".join(lines[1:])
    else:
        name = "protein"
        seq  = text
    return name, seq


def clean_sequence(seq: str) -> str:
    """Uppercase, strip whitespace/digits/special chars, keep amino acids.

    Non-standard codes (B, Z, U, O, X) are silently removed.
    Raises ValueError for sequences outside length bounds.
    """
    cleaned = re.sub(r"[^A-Za-z:]", "", seq).upper()
    # For multimers, validate each chain separately
    chains = cleaned.split(":")
    valid_chains = []
    for chain in chains:
        chain_clean = "".join(c for c in chain if c in VALID_AA)
        invalid = set(chain) - VALID_AA
        if invalid:
            logger.warning(f"Removed non-standard residues: {invalid}")
        valid_chains.append(chain_clean)
    result = ":".join(valid_chains)

    total_len = sum(len(c) for c in valid_chains)
    if total_len < MIN_SEQ_LEN:
        raise ValueError(
            f"Sequence too short: {total_len} < {MIN_SEQ_LEN} residues.\n{INPUT_FORMAT_HINT}"
        )
    if total_len > MAX_SEQ_LEN:
        raise ValueError(
            f"Sequence too long: {total_len} > {MAX_SEQ_LEN} residues (CPU limit).\n"
            f"For longer sequences, use a GPU-accelerated environment."
        )
    return result


def _confidence_label(plddt: float) -> str:
    if plddt >= PLDDT_VERY_HIGH:
        return "very high"
    if plddt >= PLDDT_HIGH:
        return "high"
    if plddt >= PLDDT_LOW:
        return "low"
    return "very low (likely disordered)"


# ── Core inference ───────────────────────────────────────────────────────────

def predict(
    sequence: str,
    output_pdb: str,
    num_recycles: Optional[int] = None,
    chunk_size: Optional[int] = None,
) -> dict:
    """Run ESMFold inference and write PDB file.

    Args:
        sequence:      Cleaned amino acid sequence (from clean_sequence()).
        output_pdb:    Output PDB file path.
        num_recycles:  Recycling iterations (default: 4, range: 1–20).
                       More recycles = higher quality but slower.
        chunk_size:    Attention chunk size for memory reduction (default: None).
                       Use 64 or 128 if OOM errors occur.

    Returns:
        dict with keys: pdb, mean_plddt, plddt_per_residue, ptm, seq_len,
                        inference_time_s, confidence_label.
    """
    model = get_model()

    if chunk_size is not None:
        model.set_chunk_size(chunk_size)

    logger.info(f"Running ESMFold inference: len={sum(len(c) for c in sequence.split(':'))}, "
                f"num_recycles={num_recycles or 4}")
    t0 = time.time()

    with torch.no_grad():
        output = model.infer(sequence, num_recycles=num_recycles)

    elapsed = time.time() - t0
    logger.info(f"Inference complete in {elapsed:.1f}s")

    # Convert output dict to PDB string
    from esm.esmfold.v1.misc import output_to_pdb
    pdb_str = output_to_pdb(output)[0]
    Path(output_pdb).write_text(pdb_str)
    logger.info(f"Saved PDB: {output_pdb}")

    # Extract confidence scores
    mean_plddt   = float(output["mean_plddt"][0].item())
    plddt_per_res = output["plddt"][0].mean(dim=-1).cpu().tolist()  # per residue
    ptm           = float(output["ptm"][0].item()) if "ptm" in output else None
    seq_len       = sum(len(c) for c in sequence.split(":"))

    return {
        "pdb":               output_pdb,
        "mean_plddt":        round(mean_plddt, 2),
        "plddt_per_residue": [round(v, 2) for v in plddt_per_res],
        "ptm":               round(ptm, 4) if ptm is not None else None,
        "seq_len":           seq_len,
        "inference_time_s":  round(elapsed, 1),
        "confidence_label":  _confidence_label(mean_plddt),
        "confidence_summary": {
            "very_high_pct": round(100 * sum(v >= PLDDT_VERY_HIGH for v in plddt_per_res) / len(plddt_per_res), 1),
            "high_pct":      round(100 * sum(PLDDT_HIGH <= v < PLDDT_VERY_HIGH for v in plddt_per_res) / len(plddt_per_res), 1),
            "low_pct":       round(100 * sum(PLDDT_LOW <= v < PLDDT_HIGH for v in plddt_per_res) / len(plddt_per_res), 1),
            "very_low_pct":  round(100 * sum(v < PLDDT_LOW for v in plddt_per_res) / len(plddt_per_res), 1),
        },
    }


# ── pLDDT visualization ──────────────────────────────────────────────────────

def plot_plddt(plddt_per_residue: list, output_png: str, protein_name: str = "Protein") -> str:
    """Generate per-residue pLDDT confidence plot."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np

    scores = np.array(plddt_per_residue)
    x = np.arange(1, len(scores) + 1)

    _, ax = plt.subplots(figsize=(max(8, len(scores) / 15), 4))

    # Color each bar by confidence category
    colors = []
    for s in scores:
        if s >= PLDDT_VERY_HIGH:
            colors.append("#1d6fa4")   # dark blue
        elif s >= PLDDT_HIGH:
            colors.append("#62b4e8")   # light blue
        elif s >= PLDDT_LOW:
            colors.append("#f5c400")   # yellow
        else:
            colors.append("#e97b00")   # orange

    ax.bar(x, scores, color=colors, width=1.0, linewidth=0)
    ax.axhline(PLDDT_VERY_HIGH, color="#1d6fa4", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.axhline(PLDDT_HIGH,      color="#62b4e8", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.axhline(PLDDT_LOW,       color="#f5c400", linestyle="--", linewidth=0.8, alpha=0.6)

    ax.set_xlim(0.5, len(scores) + 0.5)
    ax.set_ylim(0, 100)
    ax.set_xlabel("Residue position")
    ax.set_ylabel("pLDDT")
    ax.set_title(f"{protein_name} — per-residue pLDDT confidence\n"
                 f"(mean: {scores.mean():.1f})")

    legend = [
        mpatches.Patch(color="#1d6fa4", label=f"Very high (≥{PLDDT_VERY_HIGH})"),
        mpatches.Patch(color="#62b4e8", label=f"High ({PLDDT_HIGH}–{PLDDT_VERY_HIGH})"),
        mpatches.Patch(color="#f5c400", label=f"Low ({PLDDT_LOW}–{PLDDT_HIGH})"),
        mpatches.Patch(color="#e97b00", label=f"Very low (<{PLDDT_LOW})"),
    ]
    ax.legend(handles=legend, loc="lower right", fontsize=8)

    plt.tight_layout()
    plt.savefig(output_png, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved pLDDT plot: {output_png}")
    return output_png
