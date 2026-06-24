# plantgenewiki

Reusable core package for PlantGeneWiki.

This package is intentionally minimal for now. It provides a stable location for core abstractions that should not remain scattered across scripts or application prototypes.

## Planned Modules

- datasets/: Dataset registry models, path resolution, source metadata, version status, and processing state.
- importers/: reusable source-specific import logic for PGCP, NCBI, BRAD, literature, archived IMP materials, and future sources.
- normalize/: source-independent parsing, field normalization, identifier cleanup, and entity alignment helpers.
- provenance/: source, batch, checksum, parser version, and transformation trace records.
- objects/: knowledge object models such as Species, Gene, Orthogroup, Trait, Literature, Pathway, Cultivar, Dataset, and Topic.
- evidence/: EvidenceClaim records, confidence, review status, and evidence-source links.
- graph/: graph nodes, edges, schema mapping, graph export/import, and relationship queries.
- wiki/: Wiki page generation, page templates, object-to-Markdown rendering, and page update logic.
- utils/: shared utilities that are used by multiple core modules.

## Migration Policy

Move code into this package only when it is reusable across more than one workflow, application, or test. Keep source-specific crawl scripts and one-off batch jobs under scripts/ until their reusable logic becomes clear.
