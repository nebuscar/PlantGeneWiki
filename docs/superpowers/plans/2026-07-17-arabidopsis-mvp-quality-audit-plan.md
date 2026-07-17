# Arabidopsis MVP Quality Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add a reproducible quality gate for the normalized Arabidopsis thaliana MVP dataset and generate its first audit report.

**Architecture:** A streaming Python audit module reads one normalized species directory, compares JSONL counts with its manifest, validates object identifiers and coordinates, measures cross-object coverage, and checks relation endpoints. A maintenance CLI writes a stable JSON report; an architecture document defines pass criteria and distinguishes engineering integrity from biological curation quality.

**Tech Stack:** Python 3.12 standard library, JSONL, unittest, Markdown.

## Global Constraints

- Audit normalized data only; never modify raw source files.
- Keep the implementation source-agnostic and species-agnostic.
- Do not load sequence strings or the complete multi-species graph into memory.
- Do not expose internal absolute paths in committed reports.
- Use concise English comments and numbered stage headings.
- Add behavior through failing tests before implementation.

---

### Task 1: Define the species audit contract

**Files:**
- Create: `tests/quality/test_species_audit.py`
- Create: `src/phytoatlas/quality/__init__.py`
- Create: `src/phytoatlas/quality/species_audit.py`

**Interfaces:**
- Produces: `audit_species_directory(species_dir: str | Path) -> dict[str, Any]`.
- Report fields: `species_id`, `status`, `metrics`, `issues`, and `audited_at`.

- [x] Write fixtures for a complete one-gene species directory.
- [x] Verify tests fail because the audit module does not exist.
- [x] Implement streaming counts, duplicate checks, coordinate validation, coverage metrics, manifest validation, and relation endpoint validation.
- [x] Verify focused tests pass.
- [x] Commit the tested audit library.

### Task 2: Add the maintenance CLI and acceptance criteria

**Files:**
- Create: `scripts/maintenance/audit_species_mvp.py`
- Create: `docs/architecture/arabidopsis-mvp-acceptance.md`
- Test: `tests/quality/test_species_audit.py`

**Interfaces:**
- CLI consumes `--species-dir` and optional `--output`.
- CLI exits `0` for pass and `1` for fail after writing JSON.

- [x] Add a failing CLI test for report output and exit status.
- [x] Implement the minimal CLI.
- [x] Document required files, metrics, thresholds, and non-goals.
- [x] Verify focused and repository test suites pass.
- [x] Commit the CLI and acceptance document.

### Task 3: Audit production Arabidopsis data

**Files:**
- Read: normalized Arabidopsis species directory.
- Generate outside Git: external Arabidopsis quality report.

**Interfaces:**
- Consumes the normalized production directory.
- Produces a machine-readable report and a concise issue summary.

- [x] Run the CLI against production data.
- [x] Review every failed check and separate metadata defects from normalization defects.
- [x] Correct only deterministic metadata defects covered by tests.
- [x] Re-run the audit and record remaining biological or model-design issues.
- [x] Run all API, normalization, configuration, and frontend tests before completion.
