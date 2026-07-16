# src

This directory contains reusable PhytoAtlas library code.

Use src/ for code that is shared by multiple scripts, apps, tests, or future services. Do not put one-off command-line workflows here; those should stay under scripts/.

## Boundary

- src/: reusable core library code.
- scripts/: executable workflow entry points and batch jobs.
- apps/: runnable user-facing or service-facing applications.
- config/: source and Dataset registry templates.
- docs/: design, architecture, data layout, and operation notes.

## Initial Package

The initial package is phytoatlas.
