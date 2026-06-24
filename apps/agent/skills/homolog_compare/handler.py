from __future__ import annotations

from tools.gene_tools import query_homolog, compare_protein_props
from tools.analysis_tools import expression_query


def run(
    genus: str,
    gene_id: str,
    ref_species: str | None = None,
    min_bsr: float = 0.3,
) -> dict:
    homologs_result = query_homolog(genus, gene_id, ref_species, min_bsr)
    homolog_list    = homologs_result.get("homologs", [])

    # query_homolog 返回 {"query_species": sp, "query_gene": val}
    targets = [
        {"species": h["query_species"], "gene_id": h["query_gene"]}
        for h in homolog_list
        if h.get("query_species") and h.get("query_gene")
    ]

    protein_comparison: dict = {}
    if targets:
        protein_comparison = compare_protein_props(
            [{"species": t["species"], "gene_id": t["gene_id"]} for t in targets]
        )

    ref_expression: dict = {}
    if ref_species and gene_id:
        expr = expression_query(ref_species, [gene_id], mode="tissue", include_treatment=False)
        expr_data = expr.get("data", {})
        ref_expression = expr_data.get(gene_id, expr_data.get(gene_id.split(".")[0], {}))

    return {
        "homolog_count":      len(homolog_list),
        "homologs":           homolog_list,
        "protein_comparison": protein_comparison.get("table", []),
        "protein_stats":      protein_comparison.get("stats", {}),
        "ref_expression":     ref_expression,
        "_sources":           homologs_result.get("_sources", []) + protein_comparison.get("_sources", []),
        "_skill":             "homolog_compare",
    }
