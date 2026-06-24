---
name: homolog_compare
label: Homolog Comparative Analysis
icon: "🔗"
description: >
  Retrieve 1-to-1 orthologs (GeneTribe BSR/RBH) across all species in a genus
  for a given reference gene, compare protein properties (pI, MW, AA length)
  across orthologs, and return the reference gene's tissue expression profile.
  Use to assess conservation and divergence of a gene within a genus.
triggers:
  - "find orthologs of gene X in genus Y"
  - "compare homologs of X"
  - "how conserved is gene X across species"
  - "cross-species comparison of X"
  - "orthologs of X in genus Y"
input_schema:
  type: object
  properties:
    genus:
      type: string
      description: "Genus name, e.g. Arabidopsis"
    gene_id:
      type: string
      description: "Reference gene ID"
    ref_species:
      type: string
      description: "Reference species (optional; inferred if omitted)"
    min_bsr:
      type: number
      description: "BSR similarity threshold, default 0.3"
  required:
    - genus
    - gene_id
starter:
  label: "🔗 Homolog Comparison"
  message: "Compare orthologs of AT1G01010 across all species in the Arabidopsis genus."
---

# Homolog Comparative Analysis

## Purpose
Cross-species comparison of a gene within a genus using pre-computed 1v1
ortholog tables (GeneTribe BSR/RBH). Returns protein property differences
to reveal evolutionary divergence.

## When to Use
- User asks about orthologs, paralogs, or conservation of a gene
- User wants to know how a gene differs across related species
- Precedes expression comparison across species

## Response Guidelines
1. State the number of orthologs found and the species covered
2. Present protein property comparison as a compact table (species | pI | MW | length)
3. Highlight the most conserved and most diverged species
4. Show reference gene tissue expression as context
5. Append `_sources` provenance block
