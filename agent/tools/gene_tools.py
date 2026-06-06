"""
DB 工具：get_gene_info / query_homolog / search_by_annotation / compare_protein_props

工具层只做数据读取和过滤，不包含任何意图判断逻辑。
所有业务决策由 Orchestrator 在调用前完成。
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

from config import SPECIES_DIR, HOMOLOG_DIR


# ── 溯源辅助 ────────────────────────────────────────────────────────────────

def _species_source_files(species: str, field_types: list[str]) -> list[dict]:
    """返回该物种指定类型数据文件的路径列表，用于溯源。"""
    sdir = SPECIES_DIR / species
    mapping = {
        "structure":  lambda: next(sdir.glob("*.structure.tsv"),  None),
        "properties": lambda: next(sdir.glob("*.properties.tsv"), None),
        "annotation": lambda: next(sdir.glob("*.eggnog.tsv"),     None),
    }
    sources = []
    seen = set()
    for ft in field_types:
        finder = mapping.get(ft)
        if finder:
            f = finder()
            if f and str(f) not in seen:
                sources.append({"type": ft, "path": str(f)})
                seen.add(str(f))
    return sources


# ── 内部辅助 ────────────────────────────────────────────────────────────────

def _gene_id_base(mRNA_id: str) -> str:
    """AT1G01010.1 → AT1G01010（去掉 isoform 后缀）"""
    return re.sub(r'\.\d+$', '', mRNA_id)


@lru_cache(maxsize=256)
def _load_species_data(species: str) -> dict:
    """加载某物种的 structure / properties / eggnog，按 gene_id 索引。"""
    sdir = SPECIES_DIR / species
    if not sdir.exists():
        return {}

    result = {}

    # structure.tsv：无表头，列为 gene_id(含gene:前缀) chr start end strand
    struct_file = next(sdir.glob("*.structure.tsv"), None)
    if struct_file:
        df = pd.read_csv(struct_file, sep='\t', header=None,
                         names=["raw_id", "chromosome", "start", "end", "strand"])
        df["gene_id"] = df["raw_id"].str.replace("gene:", "", regex=False)
        for _, row in df.iterrows():
            gid = row["gene_id"]
            result.setdefault(gid, {})["structure"] = {
                "chromosome":  row["chromosome"],
                "start":       int(row["start"]),
                "end":         int(row["end"]),
                "strand":      row["strand"],
                "gene_length": int(row["end"]) - int(row["start"]),
            }

    # properties.tsv：有表头，gene_id 列实为 mRNA ID
    props_file = next(sdir.glob("*.properties.tsv"), None)
    if props_file:
        df = pd.read_csv(props_file, sep='\t')
        for _, row in df.iterrows():
            gid = _gene_id_base(str(row["gene_id"]))
            entry = result.setdefault(gid, {})
            # 同一基因有多个 isoform 时取第一个（后续不覆盖）
            if "properties" not in entry:
                entry["properties"] = {
                    "pi":          float(row["isoelectric_point"]),
                    "mol_weight":  round(float(row["molecular_weight"]) / 1000, 2),
                    "prot_length": int(row["protein_length"]),
                }

    # eggnog.tsv：有表头，gene_id 列实为 mRNA ID
    egg_file = next(sdir.glob("*.eggnog.tsv"), None)
    if egg_file:
        df = pd.read_csv(egg_file, sep='\t')
        for _, row in df.iterrows():
            gid = _gene_id_base(str(row["gene_id"]))
            entry = result.setdefault(gid, {})
            if "annotation" not in entry:
                go_raw   = str(row.get("GO",   "") or "")
                kegg_raw = str(row.get("KEGG", "") or "")
                pfam_raw = str(row.get("Pfam", "") or "")
                entry["annotation"] = {
                    "description": str(row.get("Description", "") or ""),
                    "go_terms":    [t for t in go_raw.split(",")   if t and t != "-"],
                    "kegg_ko":     [t for t in kegg_raw.split(",") if t and t != "-"],
                    "pfam_ids":    [t for t in pfam_raw.split(",") if t and t != "-"],
                }

    return result


@lru_cache(maxsize=64)
def _load_homolog(genus: str) -> pd.DataFrame | None:
    """加载属内同源 TSV，返回 DataFrame（行=ref_gene，列=各物种）。"""
    tsv = HOMOLOG_DIR / f"{genus}_homolog_1v1.tsv"
    if not tsv.exists():
        return None
    return pd.read_csv(tsv, sep='\t', index_col=0)


# ── 对外工具 ────────────────────────────────────────────────────────────────

def get_gene_info(
    species: str,
    gene_id: str,
    fields: list[str] | None = None,
) -> dict:
    """
    查询单个基因的结构 / 理化性质 / 功能注释。

    fields 默认返回全部三类。可指定子集：["structure", "properties", "annotation"]。
    """
    if fields is None:
        fields = ["structure", "properties", "annotation"]

    data = _load_species_data(species)
    if not data:
        return {"gene_id": gene_id, "species": species, "not_found": True,
                "reason": f"物种 {species} 无数据"}

    # gene_id 可能带 isoform 后缀，先尝试精确匹配再尝试 base
    entry = data.get(gene_id) or data.get(_gene_id_base(gene_id))
    if entry is None:
        return {"gene_id": gene_id, "species": species, "not_found": True,
                "reason": f"基因 {gene_id} 在 {species} 中未找到"}

    out = {"gene_id": gene_id, "species": species, "not_found": False}
    defaults = {
        "structure":   None,
        "properties":  None,
        "annotation":  {"description": "", "go_terms": [], "kegg_ko": [], "pfam_ids": []},
    }
    for f in fields:
        out[f] = entry.get(f) or defaults.get(f)
    out["_sources"] = _species_source_files(species, fields)
    return out


def query_homolog(
    genus: str,
    gene_id: str | None = None,
    ref_species: str | None = None,
    min_bsr: float = 0.3,
) -> dict:
    """
    查询属内一对一同源关系。

    gene_id 为空时返回整个属的同源概览（前 50 行）。
    homolog_1v1.tsv 中只存基因 ID，无 BSR 值；min_bsr 在有 BSR 列时生效。
    """
    df = _load_homolog(genus)
    if df is None:
        return {"genus": genus, "not_found": True,
                "reason": f"属 {genus} 无同源数据（TSV 不存在）"}

    species_list = list(df.columns)

    # 若指定参考物种，重新排列列顺序使其在第一列
    if ref_species and ref_species in species_list:
        cols = [ref_species] + [c for c in species_list if c != ref_species]
        df = df[cols]
        species_list = cols

    # 若指定 gene_id，只返回该行
    if gene_id:
        # 尝试精确 + base 匹配
        row = None
        for gid in (gene_id, _gene_id_base(gene_id)):
            if gid in df.index:
                row = df.loc[gid]
                break
        if row is None:
            return {"genus": genus, "gene_id": gene_id, "not_found": True,
                    "reason": f"基因 {gene_id} 不在 {genus} 同源表中"}

        homologs = [
            {"query_species": sp, "query_gene": val}
            for sp, val in row.items()
            if str(val) not in ("-", "nan", "")
        ]
        tsv_path = str(HOMOLOG_DIR / f"{genus}_homolog_1v1.tsv")
        return {
            "genus":      genus,
            "ref_gene":   gene_id,
            "homologs":   homologs,
            "hit_count":  len(homologs),
            "species_count": len(species_list),
            "_sources":   [{"type": "homolog", "path": tsv_path}],
        }

    # 无 gene_id：返回概览
    total_genes = len(df)
    tsv_path = str(HOMOLOG_DIR / f"{genus}_homolog_1v1.tsv")
    return {
        "genus":         genus,
        "species":       species_list,
        "species_count": len(species_list),
        "total_ref_genes": total_genes,
        "summary": f"共 {total_genes} 个参考基因，物种列表：{', '.join(species_list)}",
        "_sources": [{"type": "homolog", "path": tsv_path}],
    }


def search_by_annotation(
    species: str,
    pfam_ids:   list[str] | None = None,
    go_terms:   list[str] | None = None,
    kegg_kos:   list[str] | None = None,
    keywords:   list[str] | None = None,
    match_mode: str = "any",
    limit: int = 100,
) -> dict:
    """
    按功能注释检索基因。所有 term 由 Orchestrator 预先扩展后传入。

    match_mode="any"：命中任一 term 即返回
    match_mode="all"：必须命中所有 term（各类别内部为 OR，类别间为 AND）
    """
    data = _load_species_data(species)
    if not data:
        return {"species": species, "results": [], "total": 0,
                "reason": f"物种 {species} 无数据"}

    pfam_ids  = [p.upper() for p in (pfam_ids  or [])]
    go_terms  = [g.upper() for g in (go_terms  or [])]
    kegg_kos  = [k.upper() for k in (kegg_kos  or [])]
    keywords  = [w.lower() for w in (keywords  or [])]

    results = []
    for gid, entry in data.items():
        ann = entry.get("annotation")
        if not ann:
            continue

        desc   = ann.get("description", "").lower()
        g_pfam = [p.upper() for p in ann.get("pfam_ids", [])]
        g_go   = [g.upper() for g in ann.get("go_terms", [])]
        g_kegg = [k.upper() for k in ann.get("kegg_ko",  [])]

        matched_via = []

        if pfam_ids:
            hits = [p for p in pfam_ids if p in g_pfam]
            if hits:
                matched_via += [f"pfam:{h}" for h in hits]
        if go_terms:
            hits = [g for g in go_terms if g in g_go]
            if hits:
                matched_via += [f"go:{h}" for h in hits]
        if kegg_kos:
            hits = [k for k in kegg_kos if k in g_kegg]
            if hits:
                matched_via += [f"kegg:{h}" for h in hits]
        if keywords:
            hits = [w for w in keywords if w in desc]
            if hits:
                matched_via += [f"keyword:{h}" for h in hits]

        if match_mode == "any":
            include = bool(matched_via)
        else:  # all
            category_hits = {
                "pfam":    any(f"pfam:"    in m for m in matched_via) if pfam_ids  else True,
                "go":      any(f"go:"      in m for m in matched_via) if go_terms  else True,
                "kegg":    any(f"kegg:"    in m for m in matched_via) if kegg_kos  else True,
                "keyword": any(f"keyword:" in m for m in matched_via) if keywords  else True,
            }
            include = all(category_hits.values())

        if include:
            results.append({
                "gene_id":     gid,
                "description": ann.get("description", ""),
                "matched_via": matched_via,
                "hit_count":   len(matched_via),
            })

    results.sort(key=lambda x: x["hit_count"], reverse=True)
    return {
        "species": species,
        "results": results[:limit],
        "total":   len(results),
        "terms_used": {
            "pfam":     pfam_ids  or [],
            "go":       go_terms  or [],
            "kegg":     kegg_kos  or [],
            "keywords": keywords  or [],
        },
        "_sources": _species_source_files(species, ["annotation"]),
    }


def compare_protein_props(
    targets: list[dict],
    sort_by: str = "pi",
) -> dict:
    """
    对比多个基因的蛋白理化性质。

    targets 格式：[{"species": "Arabidopsis_thaliana", "gene_id": "AT1G01010"}, ...]
    sort_by：pi | mol_weight | prot_length
    """
    rows = []
    for t in targets:
        info = get_gene_info(t["species"], t["gene_id"], fields=["properties"])
        if info.get("not_found") or not info.get("properties"):
            rows.append({
                "species":     t["species"],
                "gene_id":     t["gene_id"],
                "pi":          None,
                "mol_weight":  None,
                "prot_length": None,
                "missing":     True,
            })
        else:
            p = info["properties"]
            rows.append({
                "species":     t["species"],
                "gene_id":     t["gene_id"],
                "pi":          p["pi"],
                "mol_weight":  p["mol_weight"],
                "prot_length": p["prot_length"],
                "missing":     False,
            })

    valid = [r for r in rows if not r["missing"]]
    if valid and sort_by in ("pi", "mol_weight", "prot_length"):
        rows = sorted(rows, key=lambda x: (x[sort_by] is None, x[sort_by] or 0))

    pi_vals  = [r["pi"]          for r in valid]
    mw_vals  = [r["mol_weight"]  for r in valid]
    len_vals = [r["prot_length"] for r in valid]

    # 汇总各物种的 properties 文件路径
    all_sources: list[dict] = []
    seen_paths: set[str] = set()
    for t in targets:
        for s in _species_source_files(t["species"], ["properties"]):
            if s["path"] not in seen_paths:
                all_sources.append(s)
                seen_paths.add(s["path"])

    return {
        "table": rows,
        "stats": {
            "pi_range":  [min(pi_vals),  max(pi_vals)]  if pi_vals  else None,
            "mw_range":  [min(mw_vals),  max(mw_vals)]  if mw_vals  else None,
            "len_range": [min(len_vals), max(len_vals)]  if len_vals else None,
        },
        "_sources": all_sources,
    }
