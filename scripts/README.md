# scripts

This directory contains executable workflow entry points and one-off batch jobs. The root level should stay small; scripts are grouped by responsibility.

## Layout

```text
scripts/
|-- importers/      # source-specific acquisition and import entry points
|   `-- pgcp/
|-- analysis/       # reusable or project-level analysis workflows
|   |-- msa/
|   |-- structure/
|   |-- enrichment/
|   |-- primer/
|-- build/          # knowledge object, relation, index, and Wiki build entry points
|-- datasets/       # Dataset registry and manifest utilities
|-- services/       # local service management scripts
|-- maintenance/    # repository/data maintenance utilities
`-- README.md
```

## Boundary

- importers/ may know about source-specific APIs, raw file layouts, download batches, and acquisition quirks. Current active importer work is PGCP-focused; IMP scripts are archived under archive/imp/.
- analysis/ contains analysis workflows that operate on FASTA, GFF, gene lists, proteins, structures, or normalized/semi-normalized data.
- build/ should generate PhytoAtlas products: objects, relations, EvidenceClaims, Wiki pages, graph exports, and vector indexes.
- datasets/ should maintain Dataset registry records, path checks, manifests, versions, and checksums.
- services/ contains scripts for running local applications, currently the agent service wrapper.
- maintenance/ contains cleanup or migration utilities that should not become product APIs.

Reusable parsing, normalization, provenance, and object-building logic should move into src/phytoatlas/ once the schema is stable.

## Data Policy

Do not write large outputs into Git-tracked paths. Use data/ or results/, both ignored by Git, and record source, batch, version, and parser information in Dataset metadata.
