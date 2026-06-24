# PlantGeneWiki Agent Prototype

This directory contains the current Chainlit-based agent prototype for PlantGeneWiki.

It is an application-layer prototype, not the core knowledge base implementation. Reusable knowledge-base logic should gradually move into src/, scripts/, config/, and docs/ as the PlantGeneWiki data model and pipeline design stabilize.

## Main Components

- app.py: Chainlit application entry point.
- orchestrator.py: Agent orchestration logic.
- config.py: Agent configuration loading.
- lit_pipeline/: Literature processing prototype.
- skills/: Agent skill handlers and skill instructions.
- tools/: Tool wrappers used by the agent.
- .chainlit/: Chainlit UI configuration.

## Local Runtime Files

The following files and directories are local runtime state and should not be committed:

- .env
- db/
- __pycache__/
- local vector stores
- local Chainlit database files

Use .env.example as the committed environment variable template.

## Boundary

New active knowledge-base workflows should not be added directly to apps/agent/ unless they are specifically part of the agent application. Data ingestion, parsing, Dataset registry handling, Wiki page generation, graph construction, and indexing pipelines should live under the project-level scripts/, src/, config/, and docs/ structure.
