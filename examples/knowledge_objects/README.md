# Example Knowledge Objects

Small normalized records used to validate the PlantGeneWiki publishing pipeline.

These files are not raw data. They are API-shaped knowledge objects, sequence records, relations, datasets, and evidence claims that can be rebuilt from real normalized data later.

```text
examples/knowledge_objects/
|-- species.jsonl
|-- genes.jsonl
|-- datasets.jsonl
|-- sequence_records.jsonl
|-- relations.jsonl
`-- evidence_claims.jsonl
```

The build script reads these files and writes published web data under `apps/web/public/data/api/`.
