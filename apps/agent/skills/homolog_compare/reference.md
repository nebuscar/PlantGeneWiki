# Homolog Compare — Data Reference

## Data Sources
| Field | File Pattern |
|-------|-------------|
| Orthologs | `{HOMOLOG_DIR}/{genus}_homolog_1v1.tsv` |
| Properties | `{SPECIES_DIR}/{species}/*.properties.tsv` |
| Expression | `{EXPRESSION_DIR}/{ref_species}/*.rnaseq.TPM.txt` |

## Output Schema
```json
{
  "homolog_count": <int>,
  "homologs": [
    { "ref_id", "ref_species", "subject_id", "subject_species", "bsr", "rbh" }
  ],
  "protein_comparison": [
    { "species", "gene_id", "pi", "mol_weight", "prot_length" }
  ],
  "ref_expression": { "<tissue>": <TPM_float> },
  "_sources": [ { "type", "path" } ],
  "_skill": "homolog_compare"
}
```

## Notes
- Ortholog table uses the first column as the reference gene index
- BSR (Bit Score Ratio) range: 0–1; RBH = reciprocal best hit flag
- `protein_comparison` is empty if no matching properties files exist
