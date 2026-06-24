# Enrichment Report — Data Reference

## Data Source
| Field | File Pattern |
|-------|-------------|
| Annotation background | `{SPECIES_DIR}/{species}/*.eggnog.tsv` |

## Statistical Method
- Test: Fisher's exact test (one-tailed, over-representation)
- Correction: Benjamini-Hochberg FDR
- Background: all genes in the species with at least one annotation

## Output Schema
```json
{
  "total_significant": <int>,
  "gene_count": <int>,
  "by_category": {
    "go_bp": [ { "term", "name", "p_value", "fdr", "count", "background", "type" } ],
    "go_mf": [ ... ],
    "go_cc": [ ... ],
    "kegg":  [ ... ]
  },
  "all_results": [ ... ],
  "_sources": [ { "type", "path" } ],
  "_skill": "enrichment_report"
}
```

## Notes
- `by_category` contains at most 10 terms per category, sorted by FDR ascending
- `all_results` contains at most 50 terms across all categories
- Returns empty lists if no terms meet the FDR threshold
- KEGG KO enrichment uses the KO column from eggnog.tsv
