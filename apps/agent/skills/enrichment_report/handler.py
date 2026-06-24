from __future__ import annotations

from tools.analysis_tools import go_kegg_enrichment


def run(species: str, gene_ids: list[str], p_threshold: float = 0.05) -> dict:
    result = go_kegg_enrichment(
        species, gene_ids,
        types=["go_bp", "go_mf", "go_cc", "kegg"],
        p_threshold=p_threshold,
    )

    # go_kegg_enrichment 直接以 go_bp/go_mf/go_cc/kegg 为顶层 key 返回列表
    categorized = {
        "go_bp": result.get("go_bp", [])[:10],
        "go_mf": result.get("go_mf", [])[:10],
        "go_cc": result.get("go_cc", [])[:10],
        "kegg":  result.get("kegg",  [])[:10],
    }

    all_terms: list[dict] = []
    for terms in categorized.values():
        all_terms.extend(terms)
    all_terms.sort(key=lambda x: x.get("p_adjusted", 1.0))

    return {
        "total_significant": sum(len(v) for v in categorized.values()),
        "gene_count":        result.get("query_size", len(gene_ids)),
        "background_size":   result.get("background_size", 0),
        "by_category":       categorized,
        "all_results":       all_terms[:50],
        "_sources":          result.get("_sources", []),
        "_skill":            "enrichment_report",
    }
