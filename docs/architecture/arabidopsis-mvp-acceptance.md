# Arabidopsis thaliana MVP Acceptance

## 1. Purpose

The Arabidopsis thaliana MVP is the first end-to-end reference dataset for PhytoAtlas. It validates that normalized genome data can be transformed into traceable knowledge objects, queried through the graph API, and rendered by the Wiki frontend.

This gate evaluates engineering integrity. It does not assert that every source annotation or biological interpretation is correct.

## 2. Required normalized files

The species directory must contain:

| File | Knowledge content |
|---|---|
| `species.jsonl` | Species object |
| `datasets.jsonl` | Source and version records |
| `genes.jsonl` | Gene objects and functional annotations |
| `gene_locations.jsonl` | Genome coordinates |
| `gene_structures.jsonl` | Transcripts, CDS, exon, and UTR structures |
| `sequence_records.jsonl` | CDS, protein, and genomic sequence metadata |
| `evidence_claims.jsonl` | Traceable annotation evidence |
| `relations.jsonl` | Structured object relations |
| `manifest.json` | Species identity and expected record counts |

## 3. Blocking checks

The MVP fails when any of the following conditions is detected:

1. A required file or manifest is missing or invalid.
2. A JSONL record cannot be parsed as an object.
3. Manifest counts differ from observed JSONL counts.
4. The manifest output directory does not identify the audited species directory.
5. Any file contains duplicate `object_id` values.
6. A gene coordinate has no sequence identifier, uses an invalid strand, starts before position 1, or ends before its start.
7. A relation source or target does not resolve to a normalized object in the same species package.

## 4. Coverage metrics

The first report records these ratios:

| Metric | MVP target |
|---|---:|
| Gene to GeneLocation | 100% |
| Gene to GeneStructure | 100% |
| Gene to EvidenceClaim | 100% |
| Gene with at least one inferred sequence | At least 95% |

Coverage below a target is a blocking quality issue. Sequence type counts are reported separately so CDS and protein coverage can be reviewed.

## 5. Reproducible command

```bash
cd /path/to/PhytoAtlas
PYTHONPATH=src .venv/bin/python scripts/maintenance/audit_species_mvp.py \
  --species-dir /path/to/normalized/arabidopsis_thaliana \
  --output /path/to/quality/arabidopsis_thaliana_mvp.json
```

Exit code `0` means the gate passed. Exit code `1` means the report was written but contains blocking issues.

## 6. Non-goals

- Literature relevance and evidence grading
- Orthology correctness
- GO or pathway biological validation
- Semantic retrieval quality
- Multi-species consistency
- Production graph-store selection
