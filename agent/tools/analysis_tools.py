"""
分析工具：expression_query / go_kegg_enrichment

工具层只按传入参数执行过滤和计算，模式选择由 Orchestrator 决定。
"""
from __future__ import annotations

import re
from functools import lru_cache

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact
from statsmodels.stats.multitest import multipletests

from config import EXPRESSION_DIR, TISSUE_KEYWORDS, TREATMENT_KEYWORDS, CONTROL_KEYWORDS
from tools.gene_tools import _load_species_data, _gene_id_base, _species_source_files


# ── 表达量 ───────────────────────────────────────────────────────────────────

def _parse_column(col: str) -> dict:
    """
    将 RNA-seq 列名解析为 tissue / condition / is_treatment / is_control。

    格式示例：
      Ath1_PRJNA336053_Ath1_flower_RNA_seq_TPM20
      Ath1_PRJNA63667_Ath1_root_KCl_treatment_24h_1_RNA_seq_TPM28
      Aca4_PRJNA248910_Mix_pod_leaf_root_RNA_seq_TPM2
    """
    # 去掉末尾的 _RNA_seq_TPM{数字}
    core = re.sub(r'_RNA_seq_TPM\d*$', '', col)
    # 去掉前缀 {abbr}_{PRJNA\d+}_{abbr}_ 共三段
    core = re.sub(r'^[^_]+_PRJNA\d+_[^_]+_', '', core)
    # 去掉末尾可能的单个数字（重复编号）
    core = re.sub(r'_\d+$', '', core)

    core_lower = core.lower()

    # 找组织
    tissue = "unknown"
    for kw in TISSUE_KEYWORDS:
        if kw in core_lower:
            tissue = kw
            break

    # 判断是否为处理实验
    is_treatment = any(kw.lower() in core_lower for kw in TREATMENT_KEYWORDS)
    is_control   = any(kw.lower() in core_lower for kw in CONTROL_KEYWORDS)
    if is_control and not is_treatment:
        is_treatment = False
    elif not is_control and not is_treatment:
        is_treatment = False   # 无处理关键词，视为正常样本

    # condition 为去掉组织名后的剩余描述
    condition = re.sub(re.escape(tissue), '', core, flags=re.IGNORECASE).strip('_')

    return {
        "tissue":       tissue,
        "condition":    condition or "normal",
        "is_treatment": is_treatment,
        "original_col": col,
    }


@lru_cache(maxsize=128)
def _load_expression(species: str) -> tuple[pd.DataFrame, list[dict], dict] | None:
    """
    加载物种表达矩阵，返回 (DataFrame, 列解析列表, base_id→mRNA_id映射)。

    表达文件用 mRNA ID（AT1G20920.1），工具层接收 base gene ID（AT1G20920），
    需要 base_id_map 做反向查找。
    """
    species_dir = EXPRESSION_DIR / species
    if not species_dir.exists():
        return None

    tpm_file = next(species_dir.glob("*.rnaseq.TPM.txt"), None)
    if not tpm_file:
        return None

    df = pd.read_csv(tpm_file, sep='\t', index_col=0)
    col_meta = [_parse_column(c) for c in df.columns]

    # 构建 base_gene_id → 第一个对应 mRNA_id 的映射
    base_id_map: dict[str, str] = {}
    for mRNA_id in df.index:
        base = _gene_id_base(str(mRNA_id))
        if base not in base_id_map:
            base_id_map[base] = str(mRNA_id)

    return df, col_meta, base_id_map


def expression_query(
    species: str,
    gene_ids: list[str],
    mode: str = "tissue",
    tissues: list[str] | None = None,
    include_treatment: bool = False,
) -> dict:
    """
    查询基因表达量。

    mode="tissue"：按组织聚合，返回各组织均值 ± 标准差
    mode="condition"：保留所有 sample 条件（不聚合）

    include_treatment=False 时仅返回对照组样本（Orchestrator 决策后传入）。
    """
    loaded = _load_expression(species)
    if loaded is None:
        return {
            "species": species, "mode": mode,
            "data": {}, "tissues_available": [],
            "warning": f"物种 {species} 无表达量数据",
        }

    df, col_meta, base_id_map = loaded

    # 过滤样本列
    keep_cols = []
    for meta in col_meta:
        if not include_treatment and meta["is_treatment"]:
            continue
        if tissues and meta["tissue"] not in tissues:
            continue
        keep_cols.append(meta)

    if not keep_cols:
        return {
            "species": species, "mode": mode,
            "data": {}, "tissues_available": list({m["tissue"] for m in col_meta}),
            "warning": "过滤条件下无可用样本列",
        }

    result_data = {}
    for gene_id in gene_ids:
        # 优先精确匹配 mRNA ID，其次用 base_id_map 找第一个 isoform
        row = None
        matched_id = gene_id
        base = _gene_id_base(gene_id)
        for cid in (gene_id, base_id_map.get(gene_id), base_id_map.get(base)):
            if cid and cid in df.index:
                row = df.loc[cid]
                matched_id = base   # 统一用 base ID 作为返回 key
                break

        if row is None:
            result_data[gene_id] = {"not_found": True}
            continue

        gene_result = {}
        if mode == "tissue":
            # 按 tissue 分组取均值
            tissue_groups: dict[str, list[float]] = {}
            for meta in keep_cols:
                t = meta["tissue"]
                val = float(row.get(meta["original_col"], 0) or 0)
                tissue_groups.setdefault(t, []).append(val)

            for tissue, vals in tissue_groups.items():
                arr = np.array(vals)
                gene_result[tissue] = {
                    "mean_tpm":  round(float(arr.mean()), 3),
                    "std_tpm":   round(float(arr.std()), 3) if len(arr) > 1 else None,
                    "n_samples": len(arr),
                }

        else:  # condition mode
            for meta in keep_cols:
                label = f"{meta['tissue']}_{meta['condition']}" if meta["condition"] != "normal" else meta["tissue"]
                val   = float(row.get(meta["original_col"], 0) or 0)
                gene_result[label] = {"tpm": round(val, 3)}

        result_data[matched_id] = gene_result

    tpm_file = next((EXPRESSION_DIR / species).glob("*.rnaseq.TPM.txt"), None)
    return {
        "species":           species,
        "mode":              mode,
        "data":              result_data,
        "tissues_available": sorted({m["tissue"] for m in col_meta}),
        "warning":           None if len(gene_ids) == len([k for k, v in result_data.items() if not v.get("not_found")]) else
                             f"{sum(1 for v in result_data.values() if v.get('not_found'))} 个基因未找到表达量数据",
        "_sources": [{"type": "expression_tpm", "path": str(tpm_file)}] if tpm_file else [],
    }


# ── GO / KEGG 富集 ──────────────────────────────────────────────────────────

def go_kegg_enrichment(
    species: str,
    gene_ids: list[str],
    types: list[str] | None = None,
    p_threshold: float = 0.05,
) -> dict:
    """
    对输入基因列表做 GO / KEGG 富集分析（Fisher 精确检验 + BH FDR 校正）。

    background = 该物种全基因组（从 eggnog.tsv 获取）。
    types 可选：go_bp / go_mf / go_cc / kegg
    """
    if types is None:
        types = ["go_bp", "go_mf", "go_cc", "kegg"]

    data = _load_species_data(species)
    if not data:
        return {"species": species, "error": f"物种 {species} 无数据"}

    # 规范化 query gene_ids
    query_set = set()
    for gid in gene_ids:
        base = _gene_id_base(gid)
        if base in data:
            query_set.add(base)
        elif gid in data:
            query_set.add(gid)

    if not query_set:
        return {"species": species, "error": "输入基因在数据库中均未找到"}

    background_size = len(data)
    query_size      = len(query_set)

    # 收集 term → gene 映射（全基因组 + query）
    def _collect_terms(gene_set, field) -> dict[str, set]:
        term_genes: dict[str, set] = {}
        for gid in gene_set:
            ann = data.get(gid, {}).get("annotation", {})
            terms = ann.get(field, [])
            for t in terms:
                if t:
                    term_genes.setdefault(t, set()).add(gid)
        return term_genes

    go_field_map = {
        "go_bp": "go_terms", "go_mf": "go_terms", "go_cc": "go_terms"
    }

    def _enrich(term_genes_bg, term_genes_query, label_prefix) -> list[dict]:
        rows = []
        terms = list(term_genes_query.keys())
        if not terms:
            return rows

        pvals, gene_counts, fold_enrichments = [], [], []
        for term in terms:
            k = len(term_genes_query.get(term, set()))
            K = len(term_genes_bg.get(term, set()))
            n = query_size
            N = background_size
            # Fisher 检验（超几何），确保矩阵值非负
            a = k
            b = max(n - k, 0)
            c = max(K - k, 0)
            d = max(N - K - b, 0)
            table = [[a, b], [c, d]]
            _, pval = fisher_exact(table, alternative="greater")
            fe = (k / n) / (K / N) if K > 0 and n > 0 else 0
            pvals.append(pval)
            gene_counts.append(k)
            fold_enrichments.append(round(fe, 2))

        # BH FDR 校正
        if pvals:
            _, padj, _, _ = multipletests(pvals, method="fdr_bh")
        else:
            padj = pvals

        for term, pval, p_adj, gc, fe in zip(terms, pvals, padj, gene_counts, fold_enrichments):
            if p_adj <= p_threshold:
                rows.append({
                    "term_id":         term,
                    "term_name":       term,   # 无 OBO 时 ID 即 name
                    "gene_count":      gc,
                    "fold_enrichment": fe,
                    "p_value":         round(float(pval), 6),
                    "p_adjusted":      round(float(p_adj), 6),
                    "genes":           sorted(term_genes_query.get(term, set())),
                })
        rows.sort(key=lambda x: x["p_adjusted"])
        return rows

    out = {
        "species": species,
        "query_size": query_size,
        "background_size": background_size,
        "_sources": _species_source_files(species, ["annotation"]),
    }

    if any(t in types for t in ("go_bp", "go_mf", "go_cc")):
        bg_go  = _collect_terms(data.keys(),  "go_terms")
        q_go   = _collect_terms(query_set,    "go_terms")
        for key in ("go_bp", "go_mf", "go_cc"):
            if key in types:
                out[key] = _enrich(bg_go, q_go, key)

    if "kegg" in types:
        bg_kegg = _collect_terms(data.keys(), "kegg_ko")
        q_kegg  = _collect_terms(query_set,   "kegg_ko")
        out["kegg"] = _enrich(bg_kegg, q_kegg, "kegg")

    return out
