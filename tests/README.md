# tests

This directory contains automated checks for PhytoAtlas code and scripts.

## Current Layout

- pgcp/: tests for PGCP download and parsing utilities.

## Target Layout

As src/phytoatlas grows, tests should mirror the package and workflow boundaries:

```text
tests/
|-- datasets/
|-- objects/
|-- evidence/
|-- graph/
|-- wiki/
|-- importers/
|   |-- pgcp/
|   `-- ncbi/
`-- scripts/
```

Do not add network-dependent tests as default unit tests. PGCP, IMP, NCBI, or BRAD live API checks should be marked or documented as smoke tests so normal test runs remain stable.

When running tests during cleanup, prefer:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -v tests
```
