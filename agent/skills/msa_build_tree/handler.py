"""
进化树构建 Skill handler

接受已修剪的比对 FASTA 路径，使用 IQ-TREE 建树并可视化。

限制：
  - 最多 30 条序列（防止长时阻塞事件循环）
  - 运行超时 300 秒（IQ-TREE 大数据集用命令行）
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import sys
_SCRIPTS = str(Path(__file__).parent.parent.parent.parent / "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from msa.msa_tree_build import build_tree
from msa.msa_tree_view import visualize_tree

MAX_SEQUENCES = 30
IQTREE_TIMEOUT = 300  # 5 分钟，与 BLAST 120s 同量级


def _check_iqtree() -> bool:
    try:
        subprocess.run(["iqtree", "--version"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _count_seqs(fasta_path: str) -> int:
    try:
        return sum(1 for line in Path(fasta_path).open() if line.startswith(">"))
    except OSError:
        return 0


def run(
    trimmed_fasta: str,
    model: str = "TEST",
    bootstrap: int = 0,
    show_bootstrap: bool = False,
) -> dict:
    # ── 工具检查 ──────────────────────────────────────────────────────────────
    if not _check_iqtree():
        return {
            "available": False,
            "message": "IQ-TREE 服务未配置，请联系管理员安装后再使用进化树功能。",
            "_skill": "msa_build_tree",
        }

    # ── 输入文件检查 ──────────────────────────────────────────────────────────
    fasta_path = Path(trimmed_fasta)
    if not fasta_path.exists():
        return {
            "available": False,
            "message": (
                f"找不到比对文件：{trimmed_fasta}\n"
                "请先调用 msa_align_trim 完成比对，再使用返回的 trimmed_fasta 路径。"
            ),
            "_skill": "msa_build_tree",
        }

    n_seqs = _count_seqs(trimmed_fasta)
    if n_seqs < 3:
        return {
            "available": False,
            "message": f"建树至少需要 3 条序列，当前只有 {n_seqs} 条。",
            "_skill": "msa_build_tree",
        }
    if n_seqs > MAX_SEQUENCES:
        return {
            "available": False,
            "message": (
                f"序列数 {n_seqs} 超过在线建树上限（{MAX_SEQUENCES} 条）。\n"
                f"请使用命令行：\n"
                f"  python3 scripts/msa/msa_toolkit.py -i {trimmed_fasta} "
                f"--tree --bootstrap {bootstrap or 0} -o <output_dir>/"
            ),
            "_skill": "msa_build_tree",
        }

    if bootstrap > 0 and bootstrap < 1000:
        bootstrap = 1000  # UFBoot 最小有效值

    # ── 输出路径（与比对文件同目录，前缀去掉 .trimmed） ────────────────────────
    stem = fasta_path.stem.removesuffix(".trimmed").removesuffix(".aligned")
    out_dir = fasta_path.parent
    tree_prefix = str(out_dir / stem)
    tree_png = out_dir / f"{stem}.tree.png"

    # ── 运行 IQ-TREE（同步，受 timeout 约束） ───────────────────────────────
    try:
        treefile = build_tree(
            trimmed_fasta,
            output_prefix=tree_prefix,
            model=model,
            threads=4,
            bootstrap=bootstrap,
            force=True,
            clean=True,
        )
    except TimeoutError:
        return {
            "available": False,
            "message": (
                f"IQ-TREE 超时（>{IQTREE_TIMEOUT}s）。序列较多或模型复杂时请使用命令行：\n"
                f"  python3 scripts/msa/msa_build_tree.py -i {trimmed_fasta} "
                f"-p {tree_prefix} -m {model}"
            ),
            "_skill": "msa_build_tree",
        }
    except RuntimeError as e:
        return {
            "available": False,
            "message": f"IQ-TREE 运行失败：{e}",
            "_skill": "msa_build_tree",
        }

    # ── 树可视化 ──────────────────────────────────────────────────────────────
    try:
        visualize_tree(treefile, str(tree_png), show_bootstrap=show_bootstrap)
    except Exception as e:
        tree_png_str = f"（可视化失败：{e}）"
    else:
        tree_png_str = str(tree_png)

    return {
        "available":   True,
        "n_sequences": n_seqs,
        "model":       model,
        "bootstrap":   bootstrap,
        "treefile":    treefile,
        "tree_png":    tree_png_str,
        "suggestion":  (
            f"进化树已构建完成（{n_seqs} 条序列，模型 {model}）。"
            + (f" bootstrap={bootstrap}。" if bootstrap >= 1000 else " 未做 bootstrap，可设置 bootstrap=1000 评估分支支持率。")
        ),
        "_sources":    [{"type": "phylogeny", "path": treefile}],
        "_skill":      "msa_build_tree",
    }
