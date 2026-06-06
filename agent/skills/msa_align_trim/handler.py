"""
多序列比对 Skill handler

接受 FASTA 格式序列文本，使用 MAFFT + trimAl 比对修剪，生成 MSA PDF。
自动检测序列类型（DNA/RNA/蛋白）和物种数量。

限制：最多 50 条序列（更大规模建议使用命令行）。
"""
from __future__ import annotations

import subprocess
import tempfile
import time
from pathlib import Path

import sys
_SCRIPTS = str(Path(__file__).parent.parent.parent.parent / "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from msa.msa_align import detect_seq_type, detect_species, validate_input
from msa.msa_pipeline import pipeline

from config import MSA_OUTPUT_DIR

MAX_SEQUENCES = 50
_TREE_SEQUENCE_WARN = 30  # 超过此数建议单独用 CLI 建树


def _check_tools() -> list[str]:
    """Return list of missing required tools."""
    missing = []
    for tool in ("mafft", "trimal"):
        try:
            subprocess.run([tool, "--version"], capture_output=True, timeout=5)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            missing.append(tool)
    return missing


def _make_job_dir(stem: str) -> Path:
    """Create a timestamped job output directory."""
    ts = time.strftime("%Y%m%d_%H%M%S")
    job_dir = MSA_OUTPUT_DIR / f"{ts}_{stem[:32]}"
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_dir


def _count_seqs(fasta_text: str) -> int:
    return sum(1 for line in fasta_text.splitlines() if line.startswith(">"))


def run(
    sequences: str,
    seq_type: str = "auto",
    trim_mode: str = "automated1",
    algo: str = "auto",
    threads: int = 4,
) -> dict:
    # ── 工具可用性检查 ────────────────────────────────────────────────────────
    missing = _check_tools()
    if missing:
        return {
            "available": False,
            "message": f"MSA 服务未配置，缺少以下工具：{', '.join(missing)}。请联系管理员安装后再使用。",
            "_skill": "msa_align_trim",
        }

    # ── 序列数量检查 ─────────────────────────────────────────────────────────
    n_seqs = _count_seqs(sequences)
    if n_seqs < 2:
        return {
            "available": False,
            "message": f"多序列比对至少需要 2 条序列，当前只提供了 {n_seqs} 条。",
            "_skill": "msa_align_trim",
        }
    if n_seqs > MAX_SEQUENCES:
        return {
            "available": False,
            "message": (
                f"当前提供了 {n_seqs} 条序列，超过在线比对上限（{MAX_SEQUENCES} 条）。\n"
                f"大规模比对请使用命令行：\n"
                f"  python3 scripts/msa/msa_toolkit.py -i input.fa -o output/ --threads 8"
            ),
            "_skill": "msa_align_trim",
        }

    # ── 写入临时 FASTA 文件 ───────────────────────────────────────────────────
    stem = f"msa_{n_seqs}seqs"
    job_dir = _make_job_dir(stem)
    input_fasta = job_dir / "input.fa"
    input_fasta.write_text(sequences.strip() + "\n", encoding="utf-8")

    # ── 验证输入并检测序列类型 ────────────────────────────────────────────────
    try:
        info = validate_input(str(input_fasta))
    except (FileNotFoundError, ValueError) as e:
        return {
            "available": False,
            "message": str(e),
            "_skill": "msa_align_trim",
        }

    effective_seq_type = seq_type if seq_type != "auto" else info["seq_type"]
    species = detect_species(str(input_fasta))
    n_species = len(species)

    # ── 运行 MAFFT + trimAl + 可视化（不建树） ───────────────────────────────
    try:
        result = pipeline(
            str(input_fasta),
            output_dir=str(job_dir),
            threads=threads,
            build_phylo=False,
            visualize_output=True,
            force=True,
            seq_type=effective_seq_type,
            algo=algo,
            trim_mode=trim_mode,
        )
    except Exception as e:
        return {
            "available": False,
            "message": f"比对失败：{e}",
            "_skill": "msa_align_trim",
        }

    # ── 统计比对长度 ─────────────────────────────────────────────────────────
    from Bio import SeqIO
    trimmed_records = list(SeqIO.parse(result["trimmed"], "fasta"))
    trimmed_len = len(trimmed_records[0].seq) if trimmed_records else 0

    # ── 构建建树建议 ─────────────────────────────────────────────────────────
    if n_species > 1 and n_seqs <= _TREE_SEQUENCE_WARN:
        tree_suggestion = (
            f"检测到 {n_species} 个物种，可进一步调用 `msa_build_tree` 构建进化树。"
            f"请将以下路径传入：trimmed_fasta='{result['trimmed']}'"
        )
    elif n_species > 1:
        tree_suggestion = (
            f"检测到 {n_species} 个物种，序列数 {n_seqs} 较多，建议使用命令行建树：\n"
            f"  python3 scripts/msa/msa_toolkit.py -i {result['trimmed']} -o {job_dir}/ --tree"
        )
    else:
        tree_suggestion = f"检测到 1 个物种（同物种比对），无需建树。"

    return {
        "available":      True,
        "seq_type":       effective_seq_type,
        "n_sequences":    n_seqs,
        "n_species":      n_species,
        "species":        species,
        "seq_len_range":  f"{info['min_len']}–{info['max_len']} bp/aa",
        "trimmed_length": trimmed_len,
        "tree_recommended": n_species > 1,
        "aligned_fasta":  result["aligned"],
        "trimmed_fasta":  result["trimmed"],
        "msa_pdf":        result.get("msa_pdf", ""),
        "suggestion":     tree_suggestion,
        "_sources":       [{"type": "msa_alignment", "path": str(job_dir)}],
        "_skill":         "msa_align_trim",
    }
