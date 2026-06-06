# Gene Report — Data Reference

## Data Sources
| Field | File Pattern |
|-------|-------------|
| Structure | `{SPECIES_DIR}/{species}/*.structure.tsv` |
| Properties | `{SPECIES_DIR}/{species}/*.properties.tsv` |
| Annotation | `{SPECIES_DIR}/{species}/*.eggnog.tsv` |
| Expression | `{EXPRESSION_DIR}/{species}/*.rnaseq.TPM.txt` |
| Literature | ChromaDB vector index under `db/chroma/` |

## Output Schema
```json
{
  "gene_info": {
    "<gene_id>": {
      "structure":   { "chromosome", "start", "end", "strand", "gene_length" },
      "properties":  { "pi", "mol_weight", "prot_length" },
      "annotation":  { "description", "go_terms", "kegg_ko", "pfam_ids" }
    }
  },
  "expression": { "<tissue>": <TPM_float> },
  "literature": [
    { "title", "authors", "year", "doi", "abstract", "score" }
  ],
  "_sources": [ { "type", "path" } ],
  "_skill": "gene_report"
}
```

## Notes
- `expression` is pre-aggregated to tissue means (control samples only)
- Literature results require papers to be indexed via the admin upload pipeline
- Returns `{}` for `gene_info` if species or gene_id is not found
