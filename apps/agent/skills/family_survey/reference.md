# Gene Family Survey — Data Reference

## Data Sources
| Field | File Pattern |
|-------|-------------|
| Annotation search | `{SPECIES_DIR}/{species}/*.eggnog.tsv` |
| Enrichment background | same eggnog.tsv (all annotated genes) |
| Expression | `{EXPRESSION_DIR}/{species}/*.rnaseq.TPM.txt` |

## Output Schema
```json
{
  "total_genes": <int>,
  "family_genes": [
    { "gene_id", "description", "go_terms", "kegg_ko", "pfam_ids" }
  ],
  "enrichment": [
    { "term", "name", "type", "p_value", "fdr", "count", "background" }
  ],
  "top5_expression": {
    "<gene_id>": { "<tissue>": <TPM_float> }
  },
  "_sources": [ { "type", "path" } ],
  "_skill": "family_survey"
}
```

## Notes
- `family_genes` capped at 50 entries in the response; `total_genes` reflects the true count
- Enrichment uses Fisher's exact test with Benjamini-Hochberg FDR correction
- `top5_expression` covers the first 5 genes in `family_genes` order
