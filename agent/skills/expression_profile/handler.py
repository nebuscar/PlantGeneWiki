from __future__ import annotations

from tools.analysis_tools import expression_query


def run(species: str, gene_ids: list[str], include_treatment: bool = False) -> dict:
    tissue_result = expression_query(species, gene_ids, mode="tissue", include_treatment=False)

    condition_result: dict = {}
    if include_treatment:
        condition_result = expression_query(species, gene_ids, mode="condition", include_treatment=True)

    # expression_query 返回 {"data": {gene_id: {tissue: {"mean_tpm": ..., ...}}}}
    tissue_data = tissue_result.get("data", {})

    top_tissues: dict[str, str] = {}
    for gid, vals in tissue_data.items():
        if not vals or (isinstance(vals, dict) and vals.get("not_found")):
            continue
        best = max(
            ((t, d.get("mean_tpm", 0)) for t, d in vals.items() if isinstance(d, dict)),
            key=lambda x: x[1],
            default=(None, 0),
        )
        if best[0]:
            top_tissues[gid] = best[0]

    return {
        "tissue_expression":    tissue_data,
        "condition_expression": condition_result.get("data", {}),
        "top_tissue_per_gene":  top_tissues,
        "tissues_available":    tissue_result.get("tissues_available", []),
        "gene_count":           len(gene_ids),
        "warning":              tissue_result.get("warning"),
        "_sources":             tissue_result.get("_sources", []),
        "_skill":               "expression_profile",
    }
