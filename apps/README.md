# apps

This directory contains runnable applications built on top of PlantGeneWiki.

Applications are different from the core knowledge-base implementation:

- apps/ contains user-facing or service-facing applications.
- src/ should contain reusable PlantGeneWiki library code when the core package is introduced.
- scripts/ should contain data ingestion, parsing, import, build, and analysis workflows.
- config/ should contain configuration templates and dataset/source registries.

## Current Applications

- agent/: Chainlit-based PlantGeneWiki agent prototype.
- web/: Astro static-first PlantGeneWiki web prototype.

## Future Candidates

Potential future applications can also live here:

- api/: backend API service for object, evidence, graph, and search queries.
- curation-ui/: manual review interface for literature screening and evidence validation.
- admin-dashboard/: monitoring dashboard for Dataset registry, update jobs, and indexing status.
- notebooks/ or lab/: interactive exploratory app if it becomes a maintained interface rather than ad-hoc analysis.

Local runtime files under apps should not be committed. Use app-specific .env.example files as templates.
