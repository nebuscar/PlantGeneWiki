"""
BLAST 序列相似性搜索 Skill handler

自动识别序列类型（核酸 → blastn，蛋白 → blastp），在指定物种数据库中执行比对。
需要服务器端安装 BLAST+ 并建库（makeblastdb）。未安装时返回配置提示。
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from config import SPECIES_DIR

# BLAST 数据库目录（可通过环境变量覆盖）
import os
BLAST_DB_DIR = Path(os.environ.get("PLANTSDB_BLAST_DB_DIR",
                    str(SPECIES_DIR.parent.parent / "blast_db")))

# 物种 → BLAST 数据库文件名前缀（自动推断）
_DB_SUFFIXES = {
    "blastn": ["genome.fa", "gene.fa", "gene.fna"],
    "blastp": ["pep.fa", "pep.faa", "protein.fa", "protein.faa"],
}


def _detect_seq_type(seq: str) -> str:
    """判断序列类型：DNA → blastn，蛋白 → blastp。"""
    clean = re.sub(r"[^A-Za-z]", "", seq).upper()
    if not clean:
        return "blastp"
    dna_count = sum(1 for c in clean if c in "ACGTUN")
    return "blastn" if dna_count / len(clean) >= 0.9 else "blastp"


def _find_db(species: str, prog: str) -> Path | None:
    """在 BLAST_DB_DIR/{species}/ 下找到对应程序的 .nhr 或 .phr 索引文件。"""
    db_dir = BLAST_DB_DIR / species
    if not db_dir.exists():
        return None
    # 每个 DB 文件 = makeblastdb 输出前缀（.nhr/.nin/.nsq 或 .phr/.pin/.psq）
    ext = ".nhr" if prog == "blastn" else ".phr"
    for f in sorted(db_dir.glob(f"*{ext}")):
        return f.with_suffix("")   # 返回不带后缀的前缀路径
    return None


def _run_blast(prog: str, db: Path, query_file: str, evalue: float, max_hits: int) -> list[dict]:
    """执行 BLAST 并解析 outfmt 6 结果。"""
    cmd = [
        prog,
        "-query",   query_file,
        "-db",      str(db),
        "-evalue",  str(evalue),
        "-max_target_seqs", str(max_hits),
        "-outfmt",  "6 qseqid sseqid pident length qlen slen evalue bitscore qcovs",
        "-num_threads", "4",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        return []

    hits = []
    for line in proc.stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) < 9:
            continue
        hits.append({
            "gene_id":    parts[1],
            "identity":   round(float(parts[2]), 1),
            "evalue":     float(parts[6]),
            "bitscore":   float(parts[7]),
            "coverage":   round(float(parts[8]), 1),
            "strong_hit": float(parts[2]) >= 80.0,
        })
    return hits


def run(
    sequence: str,
    species: list[str],
    evalue: float = 1e-5,
    max_hits: int = 10,
) -> dict:
    seq_clean  = re.sub(r"[\s>].*\n?", "", sequence).strip()
    seq_type   = _detect_seq_type(seq_clean)
    blast_prog = "blastn" if seq_type == "dna" else "blastp"
    seq_label  = "核酸（blastn）" if seq_type == "dna" else "蛋白（blastp）"

    # 检查 BLAST 是否可用
    try:
        subprocess.run([blast_prog, "-version"], capture_output=True, check=True, timeout=5)
    except Exception:
        return {
            "available":  False,
            "message":    f"BLAST 服务未配置。请联系管理员安装 BLAST+ 并建库后再使用序列比对功能。",
            "seq_type":   seq_label,
            "_skill":     "blast_search",
        }

    results: dict[str, list[dict]] = {}
    missing_db: list[str] = []

    with tempfile.NamedTemporaryFile(mode="w", suffix=".fa", delete=False) as fh:
        fh.write(f">query\n{seq_clean}\n")
        query_file = fh.name

    for sp in species:
        db = _find_db(sp, blast_prog)
        if db is None:
            missing_db.append(sp)
            continue
        hits = _run_blast(blast_prog, db, query_file, evalue, max_hits)
        # 补充物种字段
        for h in hits:
            h["species"] = sp
        results[sp] = hits

    # 合并所有命中，按 identity 排序
    all_hits = [h for sp_hits in results.values() for h in sp_hits]
    all_hits.sort(key=lambda x: (-x["identity"], x["evalue"]))

    top1 = all_hits[0] if all_hits else None

    return {
        "available":      True,
        "seq_type":       seq_label,
        "query_length":   len(seq_clean),
        "species_queried": species,
        "missing_db":     missing_db,
        "hits":           all_hits[:max_hits],
        "top_hit":        top1,
        "suggestion":     (
            f"最优命中：{top1['species']} {top1['gene_id']}（相似度 {top1['identity']}%，E-value {top1['evalue']:.2e}）。"
            f"可进一步调用 gene_report 或 homolog_compare 深入分析。"
        ) if top1 else "未找到显著命中（E-value < {evalue}）。",
        "_sources":       [{"type": "sequence", "path": str(BLAST_DB_DIR)}],
        "_skill":         "blast_search",
    }
