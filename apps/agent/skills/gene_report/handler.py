from tools.gene_tools import get_gene_info
from tools.analysis_tools import expression_query
from tools.lit_tools import search_literature


def run(species: str, gene_id: str) -> dict:
    info = get_gene_info(species, gene_id, fields=["structure", "properties", "annotation"])
    expr = expression_query(species, [gene_id], mode="tissue", include_treatment=False)
    lit  = search_literature(f"{gene_id} {species.replace('_', ' ')}", top_k=5)
    expr_data = expr.get("data", {})
    return {
        "gene_info":  info,
        "expression": expr_data.get(gene_id, expr_data.get(gene_id.split(".")[0], {})),
        "literature": lit if isinstance(lit, list) else lit.get("results", []),
        "_sources":   info.get("_sources", []) + expr.get("_sources", []),
        "_skill":     "gene_report",
    }
