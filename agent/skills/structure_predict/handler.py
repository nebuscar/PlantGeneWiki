"""
蛋白质结构预测 Skill handler（ESMFold）

通过 subprocess 调用 esmfold conda 环境中的 Python 运行预测，
避免与 agent 环境的依赖冲突（ESMFold 需 PyTorch 1.12 + openfold）。

限制：
  - 在线最大序列长度：400 残基（防止 CPU 运行超时）
  - 超时：15 分钟（含模型加载 ~60s + 推理时间）
  - 更长序列返回命令行指引

可选 Foldseek 结构相似性搜索：
  - 预测完成后自动提交 PDB 到 Foldseek 公开服务器
  - 搜索 pdb100 + afdb-swissprot，返回结构同源体列表
  - 超时默认 120s，失败时返回空结果但不中断主流程
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
import time
from pathlib import Path

from config import MSA_OUTPUT_DIR  # reuse result output base dir

# foldseek_search.py is in scripts/esmfold/ — import directly to avoid
# triggering the esmfold package __init__ (which requires torch/esm)
_ESMFOLD_SCRIPTS = str(Path(__file__).parent.parent.parent.parent / "scripts" / "esmfold")
if _ESMFOLD_SCRIPTS not in sys.path:
    sys.path.insert(0, _ESMFOLD_SCRIPTS)
import foldseek_search as _foldseek  # noqa: E402

logger = logging.getLogger(__name__)

# ESMFold-specific Python interpreter and script
ESMFOLD_PYTHON = "/home/nizhu/software/miniforge3/envs/esmfold/bin/python"
ESMFOLD_SCRIPT = str(Path(__file__).parent.parent.parent.parent / "scripts" / "esmfold" / "esmfold_predict.py")
ESMFOLD_OUTPUT_DIR = MSA_OUTPUT_DIR.parent / "result_esmfold"

VALID_AA    = set("ACDEFGHIKLMNPQRSTVWY")
MAX_SEQ_LEN = 400    # online limit (CPU ~5–10 min for 400 AA)
MIN_SEQ_LEN = 6
TIMEOUT_SEC = 900    # 15 minutes total (model load + inference)


def _check_available() -> bool:
    """Check that the esmfold environment and script exist."""
    return Path(ESMFOLD_PYTHON).exists() and Path(ESMFOLD_SCRIPT).exists()


def _clean_sequence(text: str) -> tuple[str, str]:
    """Parse and clean sequence. Returns (name, cleaned_seq)."""
    text = text.strip()
    if text.startswith(">"):
        lines = text.splitlines()
        name = lines[0][1:].split()[0] if lines else "protein"
        raw  = "".join(lines[1:])
    else:
        name = "protein"
        raw  = text

    # For multimers, validate chain by chain
    chains = raw.upper().split(":")
    clean_chains = []
    for chain in chains:
        cleaned = "".join(c for c in chain if c in VALID_AA or c.isalpha())
        cleaned = re.sub(r"[^ACDEFGHIKLMNPQRSTVWY]", "", cleaned)
        clean_chains.append(cleaned)

    return name, ":".join(clean_chains)


def _estimate_time(seq_len: int) -> str:
    """Rough estimate of inference time on CPU."""
    mins = max(2, seq_len // 80)  # ~1 min per 80 residues + 1 min model load
    return f"约 {mins}–{mins + 3} 分钟（含模型加载）"


FOLDSEEK_TIMEOUT  = 120   # seconds; Foldseek is fast for small proteins
FOLDSEEK_TOP_N    = 10


def _run_foldseek(pdb_path: str) -> dict:
    """Submit PDB to Foldseek and return parsed results (never raises)."""
    try:
        return _foldseek.search(
            pdb_path=pdb_path,
            databases=_foldseek.DEFAULT_DATABASES,
            top_n=FOLDSEEK_TOP_N,
            timeout=FOLDSEEK_TIMEOUT,
        )
    except Exception as exc:
        logger.warning(f"Foldseek search failed: {exc}")
        return {"available": False, "error": str(exc), "top_hits": []}


def run(
    sequence: str,
    name: str | None = None,
    num_recycles: int = 4,
    run_foldseek: bool = False,
) -> dict:
    # ── 工具可用性检查 ────────────────────────────────────────────────────────
    if not _check_available():
        return {
            "available": False,
            "message": (
                "ESMFold 服务未配置。请确认已安装 esmfold conda 环境。\n"
                f"预期解释器：{ESMFOLD_PYTHON}"
            ),
            "_skill": "structure_predict",
        }

    # ── 序列验证 ──────────────────────────────────────────────────────────────
    prot_name, seq = _clean_sequence(sequence)
    prot_name = name or prot_name

    total_len = sum(len(c) for c in seq.split(":"))

    if total_len < MIN_SEQ_LEN:
        return {
            "available": False,
            "message": f"序列过短：{total_len} < {MIN_SEQ_LEN} 残基。",
            "_skill": "structure_predict",
        }

    if total_len > MAX_SEQ_LEN:
        return {
            "available": False,
            "message": (
                f"序列长度 {total_len} 超过在线限制（{MAX_SEQ_LEN} 残基）。\n"
                f"请使用命令行脚本处理更长序列：\n"
                f"  conda activate esmfold\n"
                f"  python scripts/esmfold/esmfold_predict.py -s '{seq[:30]}...' -o result/result_esmfold/"
            ),
            "_skill": "structure_predict",
        }

    if num_recycles < 1 or num_recycles > 8:
        num_recycles = max(1, min(num_recycles, 8))

    # ── 输出目录 ──────────────────────────────────────────────────────────────
    ts = time.strftime("%Y%m%d_%H%M%S")
    job_dir = ESMFOLD_OUTPUT_DIR / f"{ts}_{prot_name[:32]}"
    job_dir.mkdir(parents=True, exist_ok=True)

    est_time = _estimate_time(total_len)

    # ── 调用 esmfold_predict.py（使用专用 Python 解释器） ────────────────────
    cmd = [
        ESMFOLD_PYTHON,
        ESMFOLD_SCRIPT,
        "-s", seq,
        "-n", prot_name,
        "-o", str(job_dir),
        "--num-recycles", str(num_recycles),
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired:
        return {
            "available": False,
            "message": (
                f"结构预测超时（>{TIMEOUT_SEC // 60} 分钟）。\n"
                f"序列较长（{total_len} 残基）建议使用命令行：\n"
                f"  conda activate esmfold\n"
                f"  python scripts/esmfold/esmfold_predict.py -s '{seq[:30]}...' -o result/result_esmfold/"
            ),
            "_skill": "structure_predict",
        }

    if proc.returncode != 0:
        return {
            "available": False,
            "message": f"ESMFold 运行失败：{proc.stderr[-500:]}",
            "_skill": "structure_predict",
        }

    # ── 读取结果 JSON ─────────────────────────────────────────────────────────
    json_path = job_dir / f"{prot_name}.json"
    if not json_path.exists():
        return {
            "available": False,
            "message": f"预测完成但未找到结果文件：{json_path}",
            "_skill": "structure_predict",
        }

    result = json.loads(json_path.read_text())

    mean_plddt = result.get("mean_plddt", 0)
    ptm        = result.get("ptm")
    conf_summ  = result.get("confidence_summary", {})
    pdb_path   = result.get("pdb", "")

    # ── 可选 Foldseek 结构相似性搜索 ─────────────────────────────────────────
    foldseek_result: dict | None = None
    if run_foldseek and pdb_path:
        logger.info(f"Running Foldseek search for {pdb_path}")
        fs = _run_foldseek(pdb_path)
        if fs.get("top_hits"):
            best = fs["top_hits"][0]
            foldseek_result = fs
            fs_summary = (
                f"\n\nFoldseek 结构搜索（{', '.join(fs['databases'])}）"
                f"发现 {fs['total_hits']} 个结构相似体。"
                f"最佳命中：{best['target']}（{best['database']}，"
                f"prob={best['prob']:.4f}，序列一致性={best['seq_id']:.1%}）"
                + (f"，来自 {best['taxon']}" if best["taxon"] else "")
                + (f"：{best['description'][:60]}" if best["description"] else "")
                + "。"
            )
        else:
            fs_summary = "\n\nFoldseek 搜索未返回命中或搜索失败，可稍后重试。"
    else:
        fs_summary = ""

    suggestion = (
        f"结构预测完成。平均 pLDDT={mean_plddt:.1f}（{result.get('confidence_label', '')}），"
        + (f"pTM={ptm:.3f}。" if ptm else "。")
        + f"\n各置信度区间：极高≥90: {conf_summ.get('very_high_pct', 0):.0f}%，"
        + f"高70-90: {conf_summ.get('high_pct', 0):.0f}%，"
        + f"低50-70: {conf_summ.get('low_pct', 0):.0f}%，"
        + f"极低<50: {conf_summ.get('very_low_pct', 0):.0f}%。"
        + fs_summary
    )

    output = {
        "available":          True,
        "name":               prot_name,
        "seq_len":            total_len,
        "pdb":                pdb_path,
        "plddt_png":          result.get("plddt_png", ""),
        "mean_plddt":         mean_plddt,
        "ptm":                ptm,
        "confidence_label":   result.get("confidence_label", ""),
        "confidence_summary": conf_summ,
        "inference_time_s":   result.get("inference_time_s"),
        "foldseek":           foldseek_result,
        "suggestion":         suggestion,
        "_sources":           [{"type": "structure_prediction", "path": str(job_dir)}],
        "_skill":             "structure_predict",
    }
    return output
