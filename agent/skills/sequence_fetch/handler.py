"""
序列获取 Skill handler

从物种目录读取 FASTA 文件，按基因 ID 提取序列。
支持 genome / gene / CDS / pep 四类序列，单基因直接返回，批量提供文件路径。
"""
from __future__ import annotations

import re
from pathlib import Path

from config import SPECIES_DIR

# 每种序列类型的候选文件名模式（按优先级排列）
_TYPE_PATTERNS: dict[str, list[str]] = {
    "genome": ["*.genome.fa", "*.genome.fna", "*.fna", "*.fa"],
    "gene":   ["*.gene.fa",   "*.gene.fna",   "*.gene.fasta"],
    "CDS":    ["*.CDS.fa",    "*.cds.fa",     "*.CDS.fna",  "*.cds.fna"],
    "pep":    ["*.pep.fa",    "*.pep.faa",    "*.protein.fa", "*.faa"],
}

_SINGLE_SHOW_LIMIT = 1      # 少于等于此数量直接展示序列
_BATCH_SHOW_LIMIT  = 100    # 超过此数量只返回文件路径


def _find_fasta(species: str, seq_type: str) -> Path | None:
    sdir = SPECIES_DIR / species
    if not sdir.exists():
        return None
    for pattern in _TYPE_PATTERNS.get(seq_type, []):
        found = list(sdir.glob(pattern))
        if found:
            return found[0]
    return None


def _parse_fasta(path: Path) -> dict[str, str]:
    """解析 FASTA 文件，返回 {header_id: sequence} 字典。"""
    sequences: dict[str, str] = {}
    current_id: str | None = None
    buf: list[str] = []

    with path.open("r", errors="replace") as fh:
        for line in fh:
            line = line.rstrip()
            if line.startswith(">"):
                if current_id is not None:
                    sequences[current_id] = "".join(buf)
                # 取第一个空格前的 ID，去掉 gene:/mRNA: 前缀
                raw_id = line[1:].split()[0]
                current_id = re.sub(r"^(gene:|mRNA:|CDS:|protein:)", "", raw_id)
                buf = []
            elif current_id is not None:
                buf.append(line)
    if current_id is not None:
        sequences[current_id] = "".join(buf)

    return sequences


def _match_gene(sequences: dict[str, str], gene_id: str) -> str | None:
    """精确匹配或 base ID 匹配（去掉 .1/.2 等 isoform 后缀）。"""
    if gene_id in sequences:
        return sequences[gene_id]
    base = re.sub(r"\.\d+$", "", gene_id)
    # 精确 base 匹配
    if base in sequences:
        return sequences[base]
    # 前缀匹配（如 AT1G01010 → AT1G01010.1）
    for key, seq in sequences.items():
        if key.startswith(base):
            return seq
    return None


def run(
    species: str,
    gene_ids: list[str] | None = None,
    seq_type: str = "CDS",
) -> dict:
    fasta_path = _find_fasta(species, seq_type)

    if fasta_path is None:
        return {
            "found":    False,
            "message":  f"物种 {species} 的 {seq_type} 序列文件不存在，请联系管理员确认数据是否已处理。",
            "_skill":   "sequence_fetch",
        }

    # 基因组文件体积巨大，直接返回路径
    if seq_type == "genome":
        return {
            "found":       True,
            "seq_type":    seq_type,
            "species":     species,
            "file_size_mb": round(fasta_path.stat().st_size / 1_048_576, 1),
            "download_path": str(fasta_path),
            "message":     f"基因组文件较大（{round(fasta_path.stat().st_size / 1_048_576, 1)} MB），请通过服务器下载链接获取。",
            "_sources":    [{"type": "sequence", "path": str(fasta_path)}],
            "_skill":      "sequence_fetch",
        }

    # 无 gene_ids：返回全文件信息
    if not gene_ids:
        stat = fasta_path.stat()
        return {
            "found":        True,
            "seq_type":     seq_type,
            "species":      species,
            "file_path":    str(fasta_path),
            "file_size_mb": round(stat.st_size / 1_048_576, 1),
            "message":      f"全物种 {seq_type} 文件可通过服务器路径下载，共 {round(stat.st_size / 1_048_576, 1)} MB。",
            "_sources":     [{"type": "sequence", "path": str(fasta_path)}],
            "_skill":       "sequence_fetch",
        }

    # 解析 FASTA 并提取目标序列
    sequences = _parse_fasta(fasta_path)

    found:   list[dict] = []
    missing: list[str]  = []
    for gid in gene_ids:
        seq = _match_gene(sequences, gid)
        if seq:
            found.append({"gene_id": gid, "length": len(seq), "sequence": seq})
        else:
            missing.append(gid)

    # 构建展示内容
    fasta_text = ""
    preview: list[str] = []
    for item in found[:_BATCH_SHOW_LIMIT]:
        entry = f">{item['gene_id']} | {seq_type} | {item['length']} bp\n{item['sequence']}"
        preview.append(entry)
        fasta_text += entry + "\n\n"

    show_inline = len(found) <= _SINGLE_SHOW_LIMIT

    return {
        "found":         True,
        "seq_type":      seq_type,
        "species":       species,
        "total_found":   len(found),
        "total_missing": len(missing),
        "missing_genes": missing,
        "sequences":     found if show_inline else found[:3],       # LLM 展示用（前3条预览）
        "fasta_preview": fasta_text if show_inline else "\n\n".join(preview[:3]),
        "file_path":     str(fasta_path) if len(found) > _SINGLE_SHOW_LIMIT else None,
        "show_inline":   show_inline,
        "_sources":      [{"type": "sequence", "path": str(fasta_path)}],
        "_skill":        "sequence_fetch",
    }
