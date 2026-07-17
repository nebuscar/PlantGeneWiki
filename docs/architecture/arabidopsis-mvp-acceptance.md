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

## 7. Golden Gene Wiki acceptance run

Acceptance completed on 2026-07-17 against graph snapshot `pgcp_v1/phytoatlas_pgcp_v1.sqlite`.

| Check | Result |
|---|---|
| Golden gene data contract | PASS: 20 of 20 genes |
| Core Python suite | PASS: 28 tests |
| FastAPI suite | PASS: 10 tests |
| Vue suite | PASS: 31 tests |
| Production frontend build | PASS |
| Rich Gene Wiki browser smoke | PASS |
| Sparse Gene Wiki browser smoke | PASS |

Browser records:

- Rich: `http://localhost:4322/genes/Atha04G0031690.v1.36`
- Sparse: `http://localhost:4322/genes/Atha01G0000130.v1.36`

Both records rendered all nine permanent sections. The rich record showed 27 transcripts, 27 CDS records, 27 Protein records, and 54 sequence links. The sparse record showed a negative-strand location, one transcript, one CDS record, and one Protein record. Homology and Publications correctly displayed `Not available`; neither page exposed raw JSON, `source_file`, internal paths, or browser console errors.

Versioned public-ID resolution is scoped to `arabidopsis_thaliana` for this milestone, avoiding an unbounded full-graph label scan. General multi-species public-ID and alias resolution remains a documented non-goal.

## 8. Knowledge Graph usability acceptance

Acceptance completed on 2026-07-18 against graph snapshot `pgcp_v1/phytoatlas_pgcp_v1.sqlite`.

| Check | Result |
|---|---|
| Core Python suite | PASS: 30 tests |
| FastAPI suite | PASS: 16 tests |
| Vue suite | PASS: 48 tests |
| Production frontend build | PASS |
| Core graph API | PASS: 59 total, 5 core, 54 sequence relations |
| Default graph presentation | PASS: 6 real nodes and 1 derived summary |
| Sequence drawer | PASS: 27 CDS and 27 Protein records |
| Real sequence graph modes | PASS: 27 CDS and 27 Protein nodes |
| Desktop and mobile layout | PASS: no overlap or horizontal overflow |
| Route history and validation states | PASS |
| Gene Wiki deep link | PASS |
| Preview service lifecycle | PASS: strict ports and complete process-group cleanup |
| Browser console and path safety | PASS |

The six real default nodes are the center Gene, Species, two distinct Dataset nodes, GeneLocation, and GeneStructure. The derived `Sequences (54)` summary is a presentation element only. It is not stored as a graph node or interpreted as a biological relation.
