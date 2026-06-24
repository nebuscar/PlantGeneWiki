---
name: enrichment_report
label: GO/KEGG Enrichment Report
icon: "🔬"
description: >
  Run full GO/KEGG enrichment analysis on a gene list (Fisher exact test +
  Benjamini-Hochberg FDR correction). Results are grouped by category:
  GO Biological Process (BP), Molecular Function (MF), Cellular Component
  (CC), and KEGG Pathway. Top 10 significant terms per category, sorted by FDR.
triggers:
  - "enrichment analysis of these genes"
  - "what pathways are these genes in"
  - "GO/KEGG analysis of gene set"
  - "functional enrichment of differentially expressed genes"
  - "which GO terms are enriched"
input_schema:
  type: object
  properties:
    species:
      type: string
      description: "Species name, e.g. Arabidopsis_thaliana"
    gene_ids:
      type: array
      items:
        type: string
      description: "Gene ID list"
    p_threshold:
      type: number
      description: "FDR significance cutoff, default 0.05"
  required:
    - species
    - gene_ids
starter:
  label: "🔬 Enrichment Analysis"
  message: "Run GO/KEGG enrichment on these Arabidopsis_thaliana genes: AT1G01010, AT2G22840, AT3G18780."
---

# GO/KEGG Enrichment Report

## Purpose
Identify significantly over-represented biological functions and pathways
in a gene set relative to the whole-genome background.

## When to Use
- User provides a list of genes and asks for functional interpretation
- After `family_survey` to understand family functional bias
- After a differential expression analysis result

## Response Guidelines
1. Report total number of significant terms (FDR < threshold)
2. Present top terms per category in a table (term | name | FDR | count/background)
3. Highlight any FDR < 0.01 terms as highly significant
4. Draw a biological conclusion from the dominant enriched functions
5. Append `_sources` provenance block
