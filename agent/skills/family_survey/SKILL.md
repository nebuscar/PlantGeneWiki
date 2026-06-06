---
name: family_survey
label: Gene Family Survey
icon: "🌿"
description: >
  Survey a gene family in a given species by annotation terms (keywords,
  Pfam IDs, GO terms, KEGG KOs). Returns all member genes with annotations,
  GO/KEGG enrichment analysis (Fisher + BH FDR), and tissue expression for
  the top 5 representative members.
triggers:
  - "how many X family genes are in species Y"
  - "find genes with Pfam domain XX in species Y"
  - "survey the transcription factor family in Y"
  - "genes involved in pathway X in species Y"
  - "identify X gene family members"
input_schema:
  type: object
  properties:
    species:
      type: string
      description: "Species name, e.g. Arabidopsis_thaliana"
    keywords:
      type: array
      items:
        type: string
      description: "Functional keywords, e.g. ['fatty acid', 'synthase']"
    pfam_ids:
      type: array
      items:
        type: string
      description: "Pfam domain IDs, e.g. ['PF00847']"
    go_terms:
      type: array
      items:
        type: string
      description: "GO term IDs, e.g. ['GO:0003700']"
    kegg_kos:
      type: array
      items:
        type: string
      description: "KEGG KO numbers, e.g. ['K00001']"
    match_mode:
      type: string
      enum: [any, all]
      description: "Matching logic: any (OR) or all (AND). Default: any"
    limit:
      type: integer
      description: "Max genes to return, default 200"
  required:
    - species
starter:
  label: "🌿 Gene Family Survey"
  message: "Survey the AP2/ERF transcription factor family (Pfam: PF00847) in Arabidopsis_thaliana."
---

# Gene Family Survey

## Purpose
Characterize a gene family by retrieving all annotated members and
summarizing their functional enrichment and expression patterns.

## When to Use
- User wants to know the size of a gene family in a species
- User asks which genes share a domain or belong to a pathway
- Precedes deeper analysis (expression profile, enrichment) of a family

## Response Guidelines
1. Report family size (N member genes found)
2. List representative members with their annotation descriptions
3. Present top enriched GO/KEGG terms per category (BP, MF, CC, KEGG)
4. Show expression of the top 5 members (highest-expressed tissue)
5. Append `_sources` provenance block
