"""MSA module - MAFFT + trimAl + IQ-TREE + pyMSAviz.

Supports DNA, RNA, and protein sequences.
"""

from .msa_align import msa, detect_species, detect_seq_type
from .msa_trim import trim_alignment
from .msa_pipeline import pipeline
from .msa_view import visualize
from .msa_tree_build import build_tree
from .msa_tree_view import visualize_tree

__all__ = [
    "msa",
    "detect_species",
    "detect_seq_type",
    "trim_alignment",
    "pipeline",
    "visualize",
    "build_tree",
    "visualize_tree",
]
