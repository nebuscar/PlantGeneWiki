---
name: expression_profile
label: Expression Profile Analysis
icon: "📈"
description: >
  Produce a multi-dimensional expression profile for a set of genes:
  tissue-aggregated TPM means (control samples), per-gene top-expressed
  tissue, and optionally treatment/condition expression data.
  Returns a numeric matrix suitable for heatmap visualization.
triggers:
  - "expression profile of genes X, Y, Z"
  - "which tissues do these genes express in"
  - "give me expression heatmap data"
  - "expression pattern of gene X"
  - "tissue expression of gene list"
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
      description: "Gene ID list, e.g. ['AT1G01010', 'AT2G22840']"
    include_treatment:
      type: boolean
      description: "Include treatment/stress samples. Default: false"
  required:
    - species
    - gene_ids
starter:
  label: "📈 Expression Profile"
  message: "Analyze the expression profile of AT1G01010 and AT2G22840 in Arabidopsis_thaliana across all tissues."
---

# Expression Profile Analysis

## Purpose
Produce an expression matrix for a gene list, identifying tissue-specificity
and expression range. Serves as input for downstream clustering or heatmap
visualization.

## When to Use
- User asks for expression patterns of a set of genes
- User wants to identify tissue-specific genes from a list
- Precedes clustering or co-expression discussion

## Response Guidelines
1. Present a compact table: gene × tissue TPM values
2. Call out the top-expressed tissue for each gene
3. Note any genes with no expression data
4. If `include_treatment=true`, separately discuss stress-responsive patterns
5. Append `_sources` provenance block
