---
name: gene_report
label: Gene Comprehensive Report
icon: "🧬"
description: >
  Generate a full analysis report for a single gene: structure (chromosomal
  coordinates, length, strand), protein properties (pI, MW, AA length),
  functional annotation (GO/KEGG/Pfam), tissue RNA-seq expression (TPM),
  and related literature (top 5 papers). Use as the entry point for any
  gene-level investigation.
triggers:
  - "analyze gene X"
  - "give me a report on gene X"
  - "comprehensive info on X"
  - "what do we know about gene X"
  - "gene X overview"
input_schema:
  type: object
  properties:
    species:
      type: string
      description: "Species name, e.g. Arabidopsis_thaliana"
    gene_id:
      type: string
      description: "Gene ID, e.g. AT1G01010"
  required:
    - species
    - gene_id
starter:
  label: "🧬 Gene Report"
  message: "Analyze gene AT1G01010 in Arabidopsis_thaliana and give me a comprehensive report."
---

# Gene Comprehensive Report

## Purpose
Single-call entry point for a complete gene profile. Combines structure,
annotation, expression, and literature into one structured result for the
LLM to summarize.

## When to Use
- User asks for an overview or introduction to a specific gene
- User wants to understand a gene's function, location, or expression pattern
- Use before drilling into any sub-topic (expression, homologs, etc.)

## Response Guidelines
1. Lead with functional annotation and biological role
2. Follow with protein properties (pI, MW, length)
3. Highlight the tissue with highest expression
4. Cite any matching literature (author, year, DOI)
5. Append data provenance block from `_sources`
