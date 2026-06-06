# Expression Profile — Data Reference

## Data Source
| Field | File Pattern |
|-------|-------------|
| TPM matrix | `{EXPRESSION_DIR}/{species}/*.rnaseq.TPM.txt` |

## Output Schema
```json
{
  "tissue_expression": {
    "<gene_id>": { "<tissue>": <TPM_float> }
  },
  "condition_expression": {
    "<gene_id>": { "<condition_label>": <TPM_float> }
  },
  "top_tissue_per_gene": { "<gene_id>": "<tissue>" },
  "gene_count": <int>,
  "_sources": [ { "type", "path" } ],
  "_skill": "expression_profile"
}
```

## Column Parsing Rules
Sample columns follow the pattern:
```
{abbr}_{PRJNA_ID}_{abbr}_{tissue}[_{treatment}]_RNA_seq_TPM{N}
```
- Columns matching `TISSUE_KEYWORDS` with no treatment flag → tissue mode
- Columns matching `TREATMENT_KEYWORDS` → condition mode
- Control keywords: `control`, `WT`, `mock`, `CK`

## Notes
- `condition_expression` is empty unless `include_treatment=true`
- TPM values are averaged across replicates per tissue/condition
- Missing expression data returns `{}` for that gene
