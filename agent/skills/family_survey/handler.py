from __future__ import annotations

from tools.gene_tools import search_by_annotation
from tools.analysis_tools import expression_query, go_kegg_enrichment


def run(
    species: str,
    keywords:   list[str] | None = None,
    pfam_ids:   list[str] | None = None,
    go_terms:   list[str] | None = None,
    kegg_kos:   list[str] | None = None,
    match_mode: str = "any",
    limit: int = 200,
) -> dict:
    family_result = search_by_annotation(
        species,
        pfam_ids=pfam_ids, go_terms=go_terms, kegg_kos=kegg_kos,
        keywords=keywords, match_mode=match_mode, limit=limit,
    )
    # search_by_annotation 返回 {"results": [...], "total": ..., "_sources": ...}
    members  = family_result.get("results", [])
    gene_ids = [g["gene_id"] for g in members if g.get("gene_id")]

    enrichment: dict = {}
    if gene_ids:
        enrichment = go_kegg_enrichment(species, gene_ids, p_threshold=0.05)

    top5_expr: dict = {}
    if gene_ids[:5]:
        expr = expression_query(species, gene_ids[:5], mode="tissue", include_treatment=False)
        top5_expr = expr.get("data", {})

    return {
        "total_genes":     len(gene_ids),
        "family_genes":    members[:50],
        "enrichment": {
            "go_bp": enrichment.get("go_bp", [])[:10],
            "go_mf": enrichment.get("go_mf", [])[:10],
            "go_cc": enrichment.get("go_cc", [])[:10],
            "kegg":  enrichment.get("kegg",  [])[:10],
        },
        "top5_expression": top5_expr,
        "_sources":        family_result.get("_sources", []) + enrichment.get("_sources", []),
        "_skill":          "family_survey",
    }
