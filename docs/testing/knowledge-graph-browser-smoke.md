# Knowledge Graph Browser Smoke

## 1. Purpose

This smoke test verifies the route-driven Knowledge Graph workbench against the normalized Arabidopsis graph snapshot. It covers the core neighborhood, real sequence records, responsive layout, navigation state, and the Gene Wiki deep link.

The Sequence summary is presentation-derived. It is never persisted as a knowledge object or interpreted as a verified biological relation.

## 2. Start isolated services

Run from the repository root:

```bash
PHYTOATLAS_API_PORT=8002 \
PHYTOATLAS_WEB_PORT=4323 \
VITE_API_BASE_URL=http://127.0.0.1:8002 \
./scripts/services/phytoatlas.sh start

PHYTOATLAS_API_PORT=8002 \
PHYTOATLAS_WEB_PORT=4323 \
./scripts/services/phytoatlas.sh status
```

When the services run on a remote development host, create a local tunnel:

```powershell
ssh -N -L 4323:127.0.0.1:4323 -L 8002:127.0.0.1:8002 <ssh-host>
```

## 3. Live API checks

Core neighborhood:

```text
http://localhost:8002/api/graph/neighbors/gene%3Aarabidopsis_thaliana%3AAtha04G0031690.v1.36?exclude_predicate=has_sequence&limit=100
```

Expected:

- `total_edges=59`
- `matched_edges=5`
- `predicate_counts.has_sequence=54`
- five returned core edges and five related nodes
- `truncated=false`

Sequence neighborhood:

```text
http://localhost:8002/api/graph/neighbors/gene%3Aarabidopsis_thaliana%3AAtha04G0031690.v1.36?predicate=has_sequence&limit=100
```

Expected:

- `matched_edges=54`
- 54 returned edges and 54 real `SequenceRecord` nodes
- 27 CDS and 27 Protein records
- `truncated=false`

## 4. Browser routes

Bare route:

```text
http://localhost:4323/graph
```

Stable example route:

```text
http://localhost:4323/graph?center=Atha04G0031690.v1.36&species=arabidopsis_thaliana&view=core
```

Rich Gene Wiki route:

```text
http://localhost:4323/genes/Atha04G0031690.v1.36
```

## 5. Acceptance checklist

1. The bare route becomes the stable example route and loads automatically.
2. The page reports 59 source relationships and seven displayed items.
3. The core canvas contains six real nodes: Gene, Species, two distinct Dataset nodes, Location, and Structure.
4. One dashed `Sequences (54)` summary is visible, while other non-selected labels appear only on hover or selection.
5. The Sequence drawer reports CDS 27 and Protein 27 and exposes working real record links.
6. `Show in graph` for CDS renders 27 CDS nodes and no Protein nodes.
7. `Show in graph` for Protein renders 27 Protein nodes and no CDS nodes.
8. `Back to core` restores six real nodes plus the derived summary.
9. Empty-center, missing-species, not-found, and Retry states show stable user-facing messages.
10. Browser back and forward restore the core and Sequence route states.
11. The Gene Wiki `View in graph` link opens the exact stable graph route.
12. At 1280 x 720, the canvas begins near the first viewport and graph labels do not overlap.
13. At 390 x 844, controls stack, the page has no horizontal overflow, the canvas remains readable, the inspector follows the canvas, and the Sequence drawer uses the full width.
14. The browser console contains no application errors and page text exposes no internal filesystem path.

## 6. Cleanup

```bash
PHYTOATLAS_API_PORT=8002 \
PHYTOATLAS_WEB_PORT=4323 \
./scripts/services/phytoatlas.sh stop
```

Confirm that ports 8002, 4323, and 4324 have no listeners before reusing the preview environment.
